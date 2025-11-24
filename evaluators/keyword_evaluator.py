"""
Keyword coverage evaluator.
"""

from __future__ import annotations

from typing import Any, Dict, List

from data import GROUND_TRUTH


class KeywordEvaluator:
    """
    Checks presence of expected keywords in the generated response.
    """

    name = "keyword_coverage"

    @staticmethod
    def _coverage(expected: List[str], response: str) -> float:
        response_lower = response.lower()
        matches = sum(1 for kw in expected if kw.lower() in response_lower)
        return matches / len(expected) if expected else 0.0

    def evaluate(self, ticket: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        ticket_id = str(ticket["id"])
        expected = GROUND_TRUTH.get(ticket_id, {}).get("expected_keywords", [])
        response = result.get("steps", {}).get("step_3", {}).get("response", "") or ""
        coverage = round(self._coverage(expected, response), 3)
        passed = coverage >= 0.6
        reasoning = f"matched {coverage*100:.0f}% of expected keywords"
        return {"name": self.name, "score": coverage, "reasoning": reasoning, "passed": passed}
