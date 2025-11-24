"""
LLM-based faithfulness evaluator (optional; runs only if an API key is available).
"""

from __future__ import annotations

import os
from typing import Any, Dict

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


class LLMFaithfulnessEvaluator:
    name = "llm_faithfulness"

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = None
        if os.getenv("OPENAI_API_KEY") and OpenAI:
            try:
                self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except Exception as exc:
                # If client init fails (e.g., proxies arg), skip evaluator
                self.client = None
                self.init_error = str(exc)
        else:
            self.init_error = "Missing OpenAI client or key"

    def evaluate(self, ticket: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        if not self.client:
            return {
                "name": self.name,
                "score": 0.0,
                "reasoning": f"LLM faithfulness evaluator skipped ({getattr(self, 'init_error', 'no client')})",
                "passed": False,
            }

        issue = ticket.get("issue", "")
        answer = result.get("output", {}).get("answer", "")
        docs = result.get("steps", {}).get("retrieve", {}).get("docs", [])
        prompt = (
            "You are an evaluator. Determine if the answer is faithful to the provided issue and docs. "
            "Return JSON with keys: score (0-1), reasoning."
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Issue: {issue}\nDocs:\n{docs}\nAnswer:\n{answer}",
                },
            ],
        )
        content = resp.choices[0].message.content or "{}"
        try:
            import json
            parsed = json.loads(content)
            score = float(parsed.get("score", 0))
            reasoning = parsed.get("reasoning", content)
        except Exception:
            score = 0.0
            reasoning = f"Could not parse judge response: {content}"
        passed = score >= 0.6
        return {"name": self.name, "score": score, "reasoning": reasoning, "passed": passed}
