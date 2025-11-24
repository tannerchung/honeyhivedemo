"""
3-step customer support agent pipeline with tracing and deterministic fallbacks.
"""

from __future__ import annotations

import os
import re
import json
import logging
from typing import Any, Dict, List, Optional

from data import KNOWLEDGE_BASE
from tracing.tracer import Tracer

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - optional dependency for offline mode
    Anthropic = None  # type: ignore

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency for offline mode
    OpenAI = None  # type: ignore


class CustomerSupportAgent:
    """
    Routes tickets, retrieves docs, and generates responses.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-7-sonnet-20250219",
        tracer: Optional[Tracer] = None,
        version: str | None = None,
        use_llm: Optional[bool] = None,
        logger: Optional[logging.Logger] = None,
        provider: str = "anthropic",
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.tracer = tracer or Tracer()
        self.version = version or "v1"
        self.provider = provider
        self.client = None
        if provider == "anthropic" and self.api_key and Anthropic:
            self.client = Anthropic(api_key=self.api_key)
        if provider == "openai":
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and OpenAI:
                self.client = OpenAI(api_key=openai_key)
            # default OpenAI model if not explicitly set
            if model == "claude-3-7-sonnet-20250219":
                self.model = "gpt-4o-mini"

        self.use_llm = use_llm if use_llm is not None else bool(self.client)
        self.logger = logger or logging.getLogger(__name__)

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
        if self.use_llm and self.client:
            try:
                prompt = (
                    "Categorize the issue into one of: upload_errors, account_access, data_export, other. "
                    "Respond with JSON keys: category, confidence, reasoning."
                )
                if self.provider == "anthropic":
                    message = self.client.messages.create(  # type: ignore[attr-defined]
                        model=self.model,
                        max_tokens=150,
                        temperature=0,
                        system=prompt,
                        messages=[{"role": "user", "content": issue}],
                    )
                    content_text = ""
                    try:
                        content_text = message.content[0].text if hasattr(message, "content") else ""
                        parsed = json.loads(content_text)
                        output = {
                            "category": parsed.get("category", "other"),
                            "confidence": float(parsed.get("confidence", 0.5)),
                            "reasoning": parsed.get("reasoning", content_text),
                            "raw_response": (
                                message.model_dump() if hasattr(message, "model_dump") else str(message)
                            ),
                        }
                    except Exception:
                        output = self._heuristic_route(issue)
                        output["raw_response"] = {
                            "mode": "fallback_parse_error",
                            "content": content_text,
                        }
                elif self.provider == "openai":
                    resp = self.client.chat.completions.create(  # type: ignore[attr-defined]
                        model=self.model,
                        temperature=0,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": issue},
                        ],
                    )
                    content_text = resp.choices[0].message.content or "{}"
                    try:
                        parsed = json.loads(content_text)
                        output = {
                            "category": parsed.get("category", "other"),
                            "confidence": float(parsed.get("confidence", 0.5)),
                            "reasoning": parsed.get("reasoning", content_text),
                            "raw_response": resp.model_dump() if hasattr(resp, "model_dump") else str(resp),
                        }
                    except Exception:
                        output = self._heuristic_route(issue)
                        output["raw_response"] = {
                            "mode": "fallback_parse_error",
                            "content": content_text,
                        }
            except Exception as err:
                output = self._heuristic_route(issue)
                output["raw_response"] = {"mode": "fallback_on_error", "error": str(err)}
                self.use_llm = False
        else:
            output = self._heuristic_route(issue)

        self.logger.debug("route_to_category", extra={"issue": issue, "output": output})
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
        self.logger.debug("retrieve_docs", extra={"category": category, "count": len(docs)})
        self.tracer.record_step("retrieve_docs", {"category": category}, output)
        return output

    @staticmethod
    def _has_action_steps(text: str) -> bool:
        return bool(re.search(r"^\s*\d+\.", text, re.MULTILINE))

    @staticmethod
    def _build_fallback_response(
        issue: str, docs: List[str], category: str | None = None, error: Optional[Exception] = None
    ) -> tuple[str, str, Dict[str, Any]]:
        """
        Build a deterministic response that still carries useful keywords.
        """
        keyword_hints = {
            "upload_errors": "Check HTTPS, CDN cache, path/404, and mixed content settings.",
            "account_access": "SSO/IdP redirect loops, password reset link expiry (15 minutes), 2FA lockout; admins can unlock accounts from the Security page.",
            "data_export": "Exports are queued (check status page), up to 15 minutes; use JSON for >1M rows; download link expires after 24 hours.",
            "other": "Collect logs, timestamps, browser/OS/app version, and check status page.",
        }
        hint = keyword_hints.get(category or "other", keyword_hints["other"])
        steps = [
            f"Issue noted: {issue}",
            f"Review: {docs[0]}",
            f"Next: {docs[1] if len(docs) > 1 else 'Apply recommended settings.'}",
            f"Validate/Retry and verify status page. {hint}",
        ]
        response_text = (
            "Thanks for reaching out. Here's how to fix this:\n"
            f"1. {steps[0]}\n"
            f"2. {steps[1]}\n"
            f"3. {steps[2]}\n"
            f"4. {steps[3]}"
        )
        raw = {"mode": "templated", "steps": steps}
        if error:
            raw["error"] = str(error)
        return response_text, "friendly_technical", raw

    def generate_response(self, issue: str, docs: List[str], category: str | None = None) -> Dict[str, Any]:
        """
        Step 3: Generate personalized support response.
        """
        if self.use_llm and self.client:
            try:
                system_prompt = (
                    "You are a concise, friendly technical support agent. Use provided docs to craft a numbered, "
                    "actionable response. Include 2-4 steps."
                )
                if self.provider == "anthropic":
                    message = self.client.messages.create(  # type: ignore[attr-defined]
                        model=self.model,
                        max_tokens=350,
                        temperature=0,
                        system=system_prompt,
                        messages=[
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
                    raw = message.model_dump() if hasattr(message, "model_dump") else str(message)
                elif self.provider == "openai":
                    resp = self.client.chat.completions.create(  # type: ignore[attr-defined]
                        model=self.model,
                        temperature=0,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": f"Issue: {issue}\nDocs:\n" + "\n".join(docs),
                            },
                        ],
                    )
                    response_text = resp.choices[0].message.content or ""
                    tone = "friendly_technical"
                    raw = resp.model_dump() if hasattr(resp, "model_dump") else str(resp)
                else:
                    raise RuntimeError("Unsupported provider")
            except Exception as err:
                self.use_llm = False
                response_text, tone, raw = self._build_fallback_response(issue, docs, category, err)
        else:
            response_text, tone, raw = self._build_fallback_response(issue, docs, category)

        has_action_steps = self._has_action_steps(response_text)
        output = {
            "response": response_text,
            "has_action_steps": has_action_steps,
            "tone": tone,
            "raw_response": raw,
        }
        self.logger.debug(
            "generate_response",
            extra={"category": category, "has_action_steps": has_action_steps, "tone": tone},
        )
        self.tracer.record_step("generate_response", {"issue": issue, "docs": docs}, output)
        return output

    def process_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all 3 steps for a single ticket.
        """
        self.tracer.start_trace(ticket_id=str(ticket["id"]), version=self.version)

        routing = self.route_to_category(ticket["issue"])
        docs = self.retrieve_docs(routing["category"])
        response = self.generate_response(ticket["issue"], docs["docs"], category=routing["category"])

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
        self.logger.debug("process_ticket", extra={"ticket_id": ticket["id"], "category": routing["category"]})
        return result
