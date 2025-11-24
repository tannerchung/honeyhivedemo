"""
LLM-as-judge style routing evaluator (deterministic here).
"""

from __future__ import annotations

from typing import Any, Dict

from data import GROUND_TRUTH


class RoutingEvaluator:
    """
    Compares predicted category against ground truth.
    """

    name = "routing_accuracy"

    def evaluate(self, ticket: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        ticket_id = str(ticket["id"])
        expected = GROUND_TRUTH.get(ticket_id, {}).get("expected_category")
        predicted = result.get("output", {}).get("category")

        if not expected or not predicted:
            return {
                "name": self.name,
                "score": 1,
                "reasoning": "Missing expected or predicted category",
                "passed": False,
            }

        passed = expected == predicted
        score = 5 if passed else 2
        reasoning = f"expected={expected}, predicted={predicted}"
        return {"name": self.name, "score": score, "reasoning": reasoning, "passed": passed}
