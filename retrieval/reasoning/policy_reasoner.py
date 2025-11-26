# Legal → GO → Judicial reasoning

"""
Policy Reasoner
===============
Policy-specific reasoning logic.
Understands legal → GO → judicial hierarchy.
"""

from typing import List, Dict


class PolicyReasoner:
    """Reasons about policy documents using hierarchy"""
    
    def analyze_policy_hierarchy(
        self,
        results: List[Dict]
    ) -> Dict:
        """
        Analyze results through policy hierarchy lens.
        
        Args:
            results: Search results
            
        Returns:
            Policy hierarchy analysis
        """
        # Group by vertical
        by_vertical = {}
        for result in results:
            vertical = result.get("vertical", "unknown")
            if vertical not in by_vertical:
                by_vertical[vertical] = []
            by_vertical[vertical].append(result)
        
        analysis = {
            "hierarchy": {
                "constitutional": self._analyze_constitutional(by_vertical.get("legal", [])),
                "statutory": self._analyze_statutory(by_vertical.get("legal", [])),
                "administrative": self._analyze_administrative(by_vertical.get("go", [])),
                "judicial": self._analyze_judicial(by_vertical.get("judicial", [])),
                "empirical": self._analyze_empirical(by_vertical.get("data", []))
            },
            "coherence": self._assess_coherence(by_vertical),
            "gaps": self._identify_gaps(by_vertical)
        }
        
        return analysis
    
    def _analyze_constitutional(self, results: List[Dict]) -> Dict:
        """Analyze constitutional dimension"""
        if not results:
            return {"present": False}
        
        # Look for constitutional references
        constitutional_refs = []
        for result in results:
            payload = result.get("payload", {})
            text = (payload.get("text", "") or payload.get("content", "")).lower()
            
            if any(term in text for term in ["constitution", "article", "fundamental right"]):
                constitutional_refs.append({
                    "text": payload.get("text", "")[:200],
                    "score": result.get("score", 0)
                })
        
        return {
            "present": len(constitutional_refs) > 0,
            "references": constitutional_refs[:3],
            "strength": "strong" if len(constitutional_refs) > 2 else "moderate"
        }
    
    def _analyze_statutory(self, results: List[Dict]) -> Dict:
        """Analyze statutory dimension"""
        if not results:
            return {"present": False}
        
        # Extract acts and sections
        acts = set()
        sections = set()
        
        for result in results:
            payload = result.get("payload", {})
            if payload.get("act_name"):
                acts.add(payload.get("act_name"))
            if payload.get("section_number"):
                sections.add(payload.get("section_number"))
        
        return {
            "present": len(acts) > 0 or len(sections) > 0,
            "acts": list(acts)[:5],
            "sections": list(sections)[:10],
            "coverage": "comprehensive" if len(acts) > 2 else "limited"
        }
    
    def _analyze_administrative(self, results: List[Dict]) -> Dict:
        """Analyze administrative implementation"""
        if not results:
            return {"present": False}
        
        # Extract GO numbers and departments
        gos = set()
        departments = set()
        recent_gos = []
        
        for result in results:
            payload = result.get("payload", {})
            if payload.get("go_number"):
                gos.add(payload.get("go_number"))
                year = payload.get("year")
                if year and int(year) >= 2020:
                    recent_gos.append(payload.get("go_number"))
            if payload.get("department"):
                departments.add(payload.get("department"))
        
        return {
            "present": len(gos) > 0,
            "total_gos": len(gos),
            "recent_gos": recent_gos,
            "departments": list(departments)[:5],
            "implementation_status": "active" if recent_gos else "historical"
        }
    
    def _analyze_judicial(self, results: List[Dict]) -> Dict:
        """Analyze judicial interpretation"""
        if not results:
            return {"present": False}
        
        # Extract cases and courts
        cases = []
        courts = set()
        
        for result in results:
            payload = result.get("payload", {})
            if payload.get("case_number"):
                cases.append({
                    "case": payload.get("case_number"),
                    "court": payload.get("court_name"),
                    "year": payload.get("year")
                })
            if payload.get("court_name"):
                courts.add(payload.get("court_name"))
        
        return {
            "present": len(cases) > 0,
            "cases": cases[:5],
            "courts": list(courts),
            "precedent_strength": "strong" if len(cases) > 3 else "moderate"
        }
    
    def _analyze_empirical(self, results: List[Dict]) -> Dict:
        """Analyze empirical data"""
        if not results:
            return {"present": False}
        
        # Extract data sources
        sources = set()
        metrics = []
        
        for result in results:
            payload = result.get("payload", {})
            if payload.get("source"):
                sources.add(payload.get("source"))
            
            text = (payload.get("text", "") or payload.get("content", "")).lower()
            if any(term in text for term in ["percentage", "%", "statistics", "data"]):
                metrics.append(payload.get("text", "")[:150])
        
        return {
            "present": len(sources) > 0,
            "data_sources": list(sources)[:5],
            "sample_metrics": metrics[:3],
            "evidence_quality": "strong" if len(sources) > 2 else "moderate"
        }
    
    def _assess_coherence(self, by_vertical: Dict[str, List[Dict]]) -> Dict:
        """Assess coherence across verticals"""
        present_verticals = list(by_vertical.keys())
        
        # Ideal: legal, go, judicial all present
        ideal_set = {"legal", "go", "judicial"}
        present_set = set(present_verticals)
        
        coherence_score = len(ideal_set & present_set) / len(ideal_set)
        
        return {
            "score": round(coherence_score, 2),
            "present_verticals": present_verticals,
            "missing_verticals": list(ideal_set - present_set),
            "assessment": "high" if coherence_score >= 0.7 else "moderate" if coherence_score >= 0.4 else "low"
        }
    
    def _identify_gaps(self, by_vertical: Dict[str, List[Dict]]) -> List[str]:
        """Identify gaps in policy coverage"""
        gaps = []
        
        if "legal" not in by_vertical or not by_vertical["legal"]:
            gaps.append("Missing statutory foundation")
        
        if "go" not in by_vertical or not by_vertical["go"]:
            gaps.append("Missing administrative implementation details")
        
        if "judicial" not in by_vertical or not by_vertical["judicial"]:
            gaps.append("No judicial interpretation found")
        
        if "data" not in by_vertical or not by_vertical["data"]:
            gaps.append("Lacks empirical evidence")
        
        return gaps


# Global policy reasoner instance
_policy_reasoner_instance = None


def get_policy_reasoner() -> PolicyReasoner:
    """Get global policy reasoner instance"""
    global _policy_reasoner_instance
    if _policy_reasoner_instance is None:
        _policy_reasoner_instance = PolicyReasoner()
    return _policy_reasoner_instance