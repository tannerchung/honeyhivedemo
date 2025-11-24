"""
Composite evaluator for end-to-end success.
"""

from __future__ import annotations

from typing import Any, Dict


class CompositeEvaluator:
    """
    Requires routing to pass, keyword coverage >= 0.6, and action steps present.
    """

    name = "composite"

    def evaluate(self, ticket: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        evaluations = result.get("evaluations", {})
        routing_ok = evaluations.get("routing_accuracy", {}).get("passed", False)
        keyword_score = evaluations.get("keyword_coverage", {}).get("score", 0)
        steps_ok = evaluations.get("action_steps", {}).get("passed", False)

        passed = routing_ok and keyword_score >= 0.6 and steps_ok
        reasoning = (
            f"routing_ok={routing_ok}, keyword_score={keyword_score}, action_steps={steps_ok}"
        )
        return {"name": self.name, "score": passed, "reasoning": reasoning, "passed": passed}
