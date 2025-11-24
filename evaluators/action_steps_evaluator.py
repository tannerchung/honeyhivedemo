"""
Action step presence evaluator.
"""

from __future__ import annotations

import re
from typing import Any, Dict


class ActionStepsEvaluator:
    """
    Validates that the response contains numbered action steps.
    """

    name = "action_steps"
    pattern = re.compile(r"^\s*\d+\.", re.MULTILINE)

    def evaluate(self, ticket: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        response = result.get("steps", {}).get("generate", {}).get("answer", "") or ""
        has_steps = bool(self.pattern.search(response))
        reasoning = "Found numbered steps" if has_steps else "No numbered steps detected"
        return {"name": self.name, "score": has_steps, "reasoning": reasoning, "passed": has_steps}
