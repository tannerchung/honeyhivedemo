"""
Checks that the agent output is structured as expected.
"""

from __future__ import annotations

from typing import Any, Dict


class FormatEvaluator:
    name = "format_structure"

    def evaluate(self, ticket: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        output = result.get("output", {})
        answer = output.get("answer", "")
        steps = output.get("steps", [])
        passed = isinstance(answer, str) and isinstance(steps, list)
        reasoning = "answer present and steps list" if passed else "missing structured fields"
        score = 1.0 if passed else 0.0
        return {"name": self.name, "score": score, "reasoning": reasoning, "passed": passed}
