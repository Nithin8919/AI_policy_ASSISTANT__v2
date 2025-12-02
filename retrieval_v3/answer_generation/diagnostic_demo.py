"""
Diagnostic Demo - run and inspect the full diagnostic → improve → test loop
===========================================================================

This is a small executable script that wires together:
- `RetrievalEngine`
- `diagnostic_runner.quick_diagnose`
- `diagnostic_runner.diagnose_and_improve`

Usage (from project root):

    # Quick one-shot diagnostic
    python retrieval_v3/answer_generation/diagnostic_demo.py "teacher transfers"

    # Full diagnostic → improve → test cycle
    python retrieval_v3/answer_generation/diagnostic_demo.py "teacher transfers" --full
"""

import os
import sys
import argparse
from pathlib import Path

from typing import Callable

from dotenv import load_dotenv

# Ensure project root is on sys.path so `retrieval_v3` and `retrieval` can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Match main_v3 path setup
if "retrieval_v3" not in sys.path:
    sys.path.insert(0, "retrieval_v3")
if "retrieval" not in sys.path:
    sys.path.insert(0, "retrieval")

# Load environment variables (for Qdrant, Gemini, etc.)
load_dotenv()

from retrieval.retrieval_core.qdrant_client import get_qdrant_client
from retrieval.embeddings.embedder import get_embedder
from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
from retrieval_v3.answer_generation.diagnostic_runner import (
    quick_diagnose,
    diagnose_and_improve,
)


def _build_engine() -> RetrievalEngine:
    """
    Build a RetrievalEngine instance for diagnostics.

    This mirrors how `main_v3.py` initializes the engine:
    - Connects to Qdrant via `get_qdrant_client`
    - Loads the Google embedder via `get_embedder`
    - Enables LLM rewrites + LLM reranking + cache
    """
    # Connect to Qdrant and embedder the same way main_v3 does
    print("[diagnostic_demo] Connecting to Qdrant...")
    qdrant = get_qdrant_client()

    print("[diagnostic_demo] Loading embedder...")
    embedder = get_embedder()

    # GEMINI_API_KEY is picked up inside RetrievalEngine automatically
    print("[diagnostic_demo] Creating RetrievalEngine (V3)...")
    engine = RetrievalEngine(
        qdrant_client=qdrant,
        embedder=embedder,
        use_llm_rewrites=True,
        use_llm_reranking=True,
        use_cross_encoder=True,
        enable_cache=True,
        use_relation_entity=True,
    )
    return engine


def _build_diagnostic_llm() -> Callable[[str], str]:
    """
    Build the function used to run the diagnostic prompt.

    Priority:
    1. If GEMINI_API_KEY or GOOGLE_API_KEY is set, use Gemini 1.5 Flash.
    2. Otherwise, return a stub that just echoes the first 1000 chars
       so you can see the prompt shape without making network calls.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[diagnostic_demo] No GEMINI_API_KEY set – using stub diagnostic LLM.\n"
              "You will see the prompt structure, but the 'diagnostic' is just an echo.\n")

        def _stub_llm(prompt: str) -> str:
            head = prompt[:1000]
            return (
                "STUB DIAGNOSTIC LLM (no GEMINI_API_KEY set).\n\n"
                "Prompt head (first 1000 chars):\n"
                "--------------------------------\n"
                f"{head}\n\n"
                "[...]"
            )

        return _stub_llm

    # Real Gemini-backed diagnostic LLM
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        # Use standard Gemini Flash model (v1beta-compatible)
        model = genai.GenerativeModel("gemini-1.5-flash")

        def _gemini_llm(prompt: str) -> str:
            try:
                resp = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 800,
                    },
                )
                return getattr(resp, "text", "").strip()
            except Exception as e:
                # Don't crash diagnostics if Gemini call fails; return a stub report instead
                head = prompt[:1000]
                return (
                    f"DIAGNOSTIC LLM ERROR: {e}\n\n"
                    "Prompt head (first 1000 chars):\n"
                    "--------------------------------\n"
                    f"{head}\n\n"
                    "[...]"
                )

        return _gemini_llm

    except Exception as e:  # pragma: no cover - network / package issues
        print(f"[diagnostic_demo] Failed to init Gemini ({e}); falling back to stub LLM.\n")

        def _fallback_stub(prompt: str) -> str:
            head = prompt[:1000]
            return (
                "STUB DIAGNOSTIC LLM (Gemini init failed).\n\n"
                "Prompt head (first 1000 chars):\n"
                "--------------------------------\n"
                f"{head}\n\n"
                "[...]"
            )

        return _fallback_stub


def run_quick(query: str) -> None:
    """Run a single quick diagnostic for the given query."""
    engine = _build_engine()
    diagnostic_llm = _build_diagnostic_llm()

    retrieval, answer, diagnostic = quick_diagnose(
        engine=engine,
        query=query,
        diagnostic_llm=diagnostic_llm,
        diagnostic_mode="comprehensive",
    )

    print("\n=== QUERY ===")
    print(query)

    print("\n=== RETRIEVAL SUMMARY ===")
    print(f"Normalized query : {retrieval.normalized_query}")
    print(f"Verticals        : {retrieval.verticals_searched}")
    print(f"Rewrites         : {len(retrieval.rewrites)}")
    print(f"Results (final)  : {retrieval.final_count}")
    print(f"Candidates total : {retrieval.total_candidates}")
    print(f"Time (sec)       : {retrieval.processing_time:.3f}")

    print("\n=== INITIAL ANSWER SUMMARY ===")
    print(answer.summary or "[no summary]")

    print("\n=== DIAGNOSTIC REPORT (COMPREHENSIVE) ===")
    print(diagnostic)


def run_full(query: str) -> None:
    """Run the full diagnostic → improve → test cycle."""
    engine = _build_engine()
    diagnostic_llm = _build_diagnostic_llm()

    result = diagnose_and_improve(
        engine=engine,
        query=query,
        diagnostic_llm=diagnostic_llm,
        initial_mode="qa",
        improved_mode="policy_brief",
        diagnostic_mode="comprehensive",
    )

    print("\n=== QUERY ===")
    print(query)

    initial_ret = result["initial_retrieval"]
    improved_ret = result["improved_retrieval"]

    print("\n=== RETRIEVAL SUMMARY (SHARED) ===")
    print(f"Normalized query : {initial_ret.normalized_query}")
    print(f"Verticals        : {initial_ret.verticals_searched}")
    print(f"Rewrites         : {len(initial_ret.rewrites)}")
    print(f"Results (final)  : {initial_ret.final_count}")
    print(f"Candidates total : {initial_ret.total_candidates}")
    print(f"Time (sec)       : {initial_ret.processing_time:.3f}")

    print("\n=== INITIAL ANSWER SUMMARY ===")
    print(result["initial_answer"].summary or "[no summary]")
    print("Validation:", result["initial_validation"])

    print("\n=== IMPROVED ANSWER SUMMARY ===")
    print(result["improved_answer"].summary or "[no summary]")
    print("Validation:", result["improved_validation"])

    print("\n=== INITIAL DIAGNOSTIC (COMPREHENSIVE) ===")
    print(result["initial_diagnostic"])

    print("\n=== IMPROVED DIAGNOSTIC (COMPREHENSIVE) ===")
    print(result["improved_diagnostic"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run diagnostic prompts on top of the RetrievalEngine."
    )
    parser.add_argument(
        "query",
        type=str,
        help="User query to test, e.g. 'teacher transfers'",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full diagnostic → improve → test cycle instead of a single diagnostic.",
    )

    args = parser.parse_args(argv)

    if args.full:
        run_full(args.query)
    else:
        run_quick(args.query)


if __name__ == "__main__":
    main()


