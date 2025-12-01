"""
Diagnostic Runner - end-to-end diagnostic → improve → test loop
================================================================

Utility helpers that sit on top of `RetrievalEngine` and
`diagnostic_prompts.get_diagnostic_prompt` to make it easy to:

- Run the normal retrieve → answer flow
- Generate a structured diagnostic report (4-layer analysis)
- Optionally generate an improved, policy-grade answer
"""

from typing import Callable, Dict, Any, Tuple

# Handle both relative and absolute imports for diagnostic_prompts
try:
    from .diagnostic_prompts import get_diagnostic_prompt
except ImportError:
    # Fallback for when run as script directly
    try:
        from retrieval_v3.answer_generation.diagnostic_prompts import get_diagnostic_prompt
    except ImportError:
        # Last resort: add current directory to path
        import sys
        from pathlib import Path
        current_dir = Path(__file__).parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        from diagnostic_prompts import get_diagnostic_prompt

try:
    # Local import to avoid circulars at import time
    from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine, RetrievalOutput
    from retrieval_v3.answer_generation.answer_builder import Answer
except ImportError:  # pragma: no cover - for standalone usage/tests
    RetrievalEngine = Any  # type: ignore
    RetrievalOutput = Any  # type: ignore
    Answer = Any  # type: ignore


def _format_docs_for_diagnostic(
    retrieval_output: "RetrievalOutput",
    max_docs: int = 10,
) -> str:
    """
    Turn `RetrievalOutput.results` into a compact, LLM-friendly string.

    Each document is rendered as:

        [DOC i] <doc_id> (<vertical>, score=X.XX)
        GO: <go_number> | Year: <year> | Dept: <department>
        Snippet:
        <first 500 chars>
        ----
    """
    lines = []
    for i, r in enumerate(retrieval_output.results[:max_docs], 1):
        meta = getattr(r, "metadata", {}) or {}

        doc_id = getattr(r, "doc_id", f"doc_{i}")
        vertical = getattr(r, "vertical", "unknown")
        score = getattr(r, "score", 0.0)

        go_number = meta.get("go_number", "")
        year = meta.get("year", "")
        department = meta.get("department", "")

        content = getattr(r, "content", "") or meta.get("content", "") or ""
        snippet = content[:500]

        header = f"[DOC {i}] {doc_id} ({vertical}, score={score:.3f})"
        meta_line = f"GO: {go_number} | Year: {year} | Dept: {department}"

        lines.append(header)
        lines.append(meta_line)
        lines.append("Snippet:")
        lines.append(snippet)
        lines.append("----")

    return "\n".join(lines)


def _answer_to_text(answer: "Answer") -> str:
    """
    Flatten `Answer` into a single text blob for diagnostics.
    """
    if answer is None:
        return ""

    parts = [answer.summary or ""]

    for name, content in (answer.sections or {}).items():
        if not content:
            continue
        parts.append(f"\n## {name}\n{content}")

    return "\n".join([p for p in parts if p.strip()])


def diagnose_and_improve(
    engine: "RetrievalEngine",
    query: str,
    diagnostic_llm: Callable[[str], str],
    initial_mode: str = "qa",
    improved_mode: str = "policy_brief",
    diagnostic_mode: str = "comprehensive",
) -> Dict[str, Any]:
    """
    Run a full diagnostic → improve → test cycle for a single query.

    Args:
        engine:   RetrievalEngine instance
        query:    User query text
        diagnostic_llm:
            Callable that takes a prompt string and returns the
            LLM's text output (e.g. `lambda p: llm.generate(p)`).
        initial_mode:
            Mode used for the first answer (e.g. "qa").
        improved_mode:
            Mode used for the second answer (e.g. "policy_brief"
            so the answer is forced into policy structure).
        diagnostic_mode:
            One of the modes supported by `get_diagnostic_prompt`:
            'comprehensive', 'retrieval', 'missing',
            'structure', 'reasoning', 'contradiction', 'full'.

    Returns:
        Dictionary with:
            - initial_retrieval: RetrievalOutput
            - initial_answer: Answer
            - initial_validation: dict
            - initial_diagnostic: str
            - improved_retrieval: RetrievalOutput
            - improved_answer: Answer
            - improved_validation: dict
            - improved_diagnostic: str
    """
    # STEP 1: Baseline run (retrieve + answer + validate)
    initial_retrieval, initial_answer, initial_validation = engine.retrieve_and_answer(
        query=query,
        mode=initial_mode,
        validate_answer=True,
    )

    docs_str = _format_docs_for_diagnostic(initial_retrieval)
    answer_text = _answer_to_text(initial_answer)

    # STEP 2: Diagnostic on baseline answer
    diagnostic_prompt = get_diagnostic_prompt(
        query=query,
        documents=docs_str,
        answer=answer_text,
        mode=diagnostic_mode,
    )
    initial_diagnostic = diagnostic_llm(diagnostic_prompt)

    # STEP 3: Improved run – keep retrieval, but force a stronger answer structure
    # Reuse the same retrieval output to avoid extra Qdrant calls.
    improved_retrieval = initial_retrieval

    # Convert RetrievalResult list into the dict format expected by AnswerBuilder
    improved_builder_input = []
    for r in improved_retrieval.results:
        meta = getattr(r, "metadata", {}) or {}
        improved_builder_input.append(
            {
                "content": getattr(r, "content", "") or meta.get("content", ""),
                "chunk_id": getattr(r, "chunk_id", ""),
                "doc_id": getattr(r, "doc_id", ""),
                "score": getattr(r, "score", 0.0),
                "vertical": getattr(r, "vertical", "unknown"),
                "metadata": meta,
                "url": meta.get("url"),
            }
        )

    # Use the internal AnswerBuilder but with a different mode
    improved_answer = engine.answer_builder.build_answer(
        query=query,
        results=improved_builder_input,
        mode=improved_mode,
    )

    # Re‑run validation on the improved answer
    improved_answer_dict = {
        "summary": improved_answer.summary,
        "sections": improved_answer.sections,
        "citations": improved_answer.citations,
        "confidence": improved_answer.confidence,
        "metadata": improved_answer.metadata,
    }
    is_valid, issues = engine.answer_validator.validate_answer(
        improved_answer_dict,
        improved_builder_input,
        query,
    )
    quality_score = engine.answer_validator.get_quality_score(
        improved_answer_dict,
        improved_builder_input,
        query,
    )
    suggestions = engine.answer_validator.suggest_improvements(
        improved_answer_dict,
        improved_builder_input,
        query,
    )

    improved_validation = {
        "is_valid": is_valid,
        "issues": issues,
        "quality_score": quality_score,
        "suggestions": suggestions,
    }

    # STEP 4: Diagnostic on improved answer
    improved_docs_str = _format_docs_for_diagnostic(improved_retrieval)
    improved_answer_text = _answer_to_text(improved_answer)

    improved_diag_prompt = get_diagnostic_prompt(
        query=query,
        documents=improved_docs_str,
        answer=improved_answer_text,
        mode=diagnostic_mode,
    )
    improved_diagnostic = diagnostic_llm(improved_diag_prompt)

    return {
        "initial_retrieval": initial_retrieval,
        "initial_answer": initial_answer,
        "initial_validation": initial_validation,
        "initial_diagnostic": initial_diagnostic,
        "improved_retrieval": improved_retrieval,
        "improved_answer": improved_answer,
        "improved_validation": improved_validation,
        "improved_diagnostic": improved_diagnostic,
    }


def quick_diagnose(
    engine: "RetrievalEngine",
    query: str,
    diagnostic_llm: Callable[[str], str],
    diagnostic_mode: str = "comprehensive",
) -> Tuple["RetrievalOutput", "Answer", str]:
    """
    Lightweight helper: just run retrieve → answer and one diagnostic.

    This is close to the pseudocode you described:

        retrieval, answer, _ = engine.retrieve_and_answer(query)
        docs = _format_docs_for_diagnostic(retrieval)
        prompt = get_diagnostic_prompt(query, docs, answer_text, mode)
        diagnostic = llm(prompt)
    """
    retrieval_output, answer, _ = engine.retrieve_and_answer(
        query=query,
        mode="qa",
        validate_answer=True,
    )

    docs_str = _format_docs_for_diagnostic(retrieval_output)
    answer_text = _answer_to_text(answer)

    diagnostic_prompt = get_diagnostic_prompt(
        query=query,
        documents=docs_str,
        answer=answer_text,
        mode=diagnostic_mode,
    )
    diagnostic_text = diagnostic_llm(diagnostic_prompt)

    return retrieval_output, answer, diagnostic_text


if __name__ == "__main__":
    print("=" * 80)
    print("Diagnostic Runner - Usage Examples")
    print("=" * 80)
    print()
    print("This module provides two main functions:")
    print()
    print("1. quick_diagnose(engine, query, diagnostic_llm, diagnostic_mode='comprehensive')")
    print("   - Runs retrieve → answer → diagnostic in one call")
    print("   - Returns: (RetrievalOutput, Answer, diagnostic_text)")
    print()
    print("2. diagnose_and_improve(engine, query, diagnostic_llm, ...)")
    print("   - Full cycle: baseline → diagnostic → improved answer → diagnostic")
    print("   - Returns: dict with initial and improved results + diagnostics")
    print()
    print("=" * 80)
    print("Example Usage:")
    print("=" * 80)
    print("""
from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
from retrieval_v3.answer_generation.diagnostic_runner import quick_diagnose, diagnose_and_improve
import google.generativeai as genai

# Initialize engine (with your Qdrant client and embedder)
engine = RetrievalEngine(qdrant_client=qdrant, embedder=embedder)

# Setup diagnostic LLM (Gemini Flash)
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash-8b')

def diagnostic_llm(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text

# Quick diagnostic
retrieval, answer, diagnostic = quick_diagnose(
    engine=engine,
    query="teacher transfers",
    diagnostic_llm=diagnostic_llm,
    diagnostic_mode="comprehensive"
)

print("Diagnostic Report:")
print(diagnostic)

# Full improve cycle
result = diagnose_and_improve(
    engine=engine,
    query="teacher transfers",
    diagnostic_llm=diagnostic_llm,
    initial_mode="qa",
    improved_mode="policy_brief",
    diagnostic_mode="comprehensive"
)

print("\\n=== Initial Diagnostic ===")
print(result["initial_diagnostic"])

print("\\n=== Improved Diagnostic ===")
print(result["improved_diagnostic"])
""")
    print("=" * 80)
    print("Note: This is a utility module. Import it to use the functions.")
    print("=" * 80)

