"""
3-step customer support agent pipeline with tracing and deterministic fallbacks.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from data import KNOWLEDGE_BASE
from tracing.tracer import Tracer

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - optional dependency for offline mode
    Anthropic = None  # type: ignore


class CustomerSupportAgent:
    """
    Routes tickets, retrieves docs, and generates responses.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20240620",
        tracer: Optional[Tracer] = None,
        version: str | None = None,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.tracer = tracer or Tracer()
        self.version = version or "v1"
        self.client = Anthropic(api_key=self.api_key) if self.api_key and Anthropic else None

    @staticmethod
    def _heuristic_route(issue: str) -> Dict[str, Any]:
        text = issue.lower()
        if any(k in text for k in ["upload", "404", "cdn", "cache", "mixed content"]):
            category = "upload_errors"
        elif any(k in text for k in ["sso", "login", "reset", "2fa", "password", "locked"]):
            category = "account_access"
        elif any(k in text for k in ["export", "csv", "json", "download", "queue"]):
            category = "data_export"
        else:
            category = "other"
        confidence = 0.82 if category != "other" else 0.6
        return {
            "category": category,
            "confidence": confidence,
            "reasoning": f"Rule-based routing matched keywords for {category}",
            "raw_response": {"mode": "heuristic"},
        }

    def route_to_category(self, issue: str) -> Dict[str, Any]:
        """
        Step 1: Use LLM (or heuristic fallback) to categorize customer issue.
        """
        if self.client:
            prompt = (
                "Categorize the issue into one of: upload_errors, account_access, data_export, other. "
                "Respond with JSON keys: category, confidence, reasoning."
            )
            message = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                temperature=0,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": issue},
                ],
            )
            try:
                content = message.content[0].text if hasattr(message, "content") else ""
            except Exception:
                content = str(message)
            output = {
                "category": "other",
                "confidence": 0.5,
                "reasoning": content or "LLM response parsed",
                "raw_response": message,
            }
        else:
            output = self._heuristic_route(issue)

        self.tracer.record_step("route_to_category", {"issue": issue}, output)
        return output

    def retrieve_docs(self, category: str) -> Dict[str, Any]:
        """
        Step 2: Retrieve relevant documentation.
        """
        docs = KNOWLEDGE_BASE.get(category, KNOWLEDGE_BASE["other"])
        token_estimate = sum(len(d.split()) for d in docs)
        output = {
            "docs": docs,
            "source": "knowledge_base",
            "count": len(docs),
            "tokens": token_estimate,
        }
        self.tracer.record_step("retrieve_docs", {"category": category}, output)
        return output

    @staticmethod
    def _has_action_steps(text: str) -> bool:
        return bool(re.search(r"^\s*\d+\.", text, re.MULTILINE))

    def generate_response(self, issue: str, docs: List[str]) -> Dict[str, Any]:
        """
        Step 3: Generate personalized support response.
        """
        if self.client:
            system_prompt = (
                "You are a concise, friendly technical support agent. Use provided docs to craft a numbered, "
                "actionable response. Include 2-4 steps."
            )
            message = self.client.messages.create(
                model=self.model,
                max_tokens=350,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Issue: {issue}\nDocs:\n" + "\n".join(docs),
                    },
                ],
            )
            try:
                response_text = message.content[0].text if hasattr(message, "content") else ""
            except Exception:
                response_text = str(message)
            tone = "friendly_technical"
            raw = message
        else:
            steps = [
                "Verify the obvious based on docs.",
                "Apply the documented fix.",
                "Retry and confirm.",
            ]
            response_text = (
                f"Thanks for reaching out. Here's how to fix this:\n"
                f"1. Review: {docs[0]}\n"
                f"2. Next: {docs[1] if len(docs) > 1 else 'Apply recommended settings.'}\n"
                f"3. Confirm and retry your request."
            )
            tone = "friendly_technical"
            raw = {"mode": "templated", "steps": steps}

        has_action_steps = self._has_action_steps(response_text)
        output = {
            "response": response_text,
            "has_action_steps": has_action_steps,
            "tone": tone,
            "raw_response": raw,
        }
        self.tracer.record_step("generate_response", {"issue": issue, "docs": docs}, output)
        return output

    def process_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all 3 steps for a single ticket.
        """
        self.tracer.start_trace(ticket_id=str(ticket["id"]), version=self.version)

        routing = self.route_to_category(ticket["issue"])
        docs = self.retrieve_docs(routing["category"])
        response = self.generate_response(ticket["issue"], docs["docs"])

        trace = self.tracer.end_trace()
        result = {
            "ticket_id": str(ticket["id"]),
            "input": ticket,
            "steps": {
                "step_1": routing,
                "step_2": docs,
                "step_3": response,
            },
            "output": {
                "category": routing["category"],
                "response": response["response"],
            },
            "evaluations": {},
            "trace": trace,
            "version": self.version,
        }
        return result
