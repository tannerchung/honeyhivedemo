"""
Three-step customer support agent pipeline with intelligent routing and response generation.

This module implements the core customer support agent that processes support tickets
through a three-step pipeline:
    1. Route ticket to category (upload_errors, account_access, data_export, other)
    2. Retrieve relevant documentation for that category
    3. Generate a personalized, actionable response

The agent supports multiple LLM providers (Anthropic Claude, OpenAI) and includes
a deterministic heuristic fallback mode for when LLM APIs are unavailable. It's
designed to demonstrate HoneyHive tracing, evaluation, and experimentation capabilities.

Key Features:
    - Multi-provider LLM support (Anthropic, OpenAI)
    - Graceful degradation to heuristic mode when LLM unavailable
    - Comprehensive tracing with HoneyHive integration
    - Ground truth enrichment for evaluation
    - Intentional failure cases for demo purposes (Issues #3, #8)
    - Token usage tracking across providers

Architecture:
    The agent uses a pipeline pattern where each step produces outputs consumed
    by the next step. Each step is independently traced and can fail gracefully.
    The @trace decorator wraps each step for observability.

Demo-Specific Behavior:
    - Heuristic routing intentionally fails on ambiguous cases (e.g., "download")
      to demonstrate error cascades in the demo (see Issues #3 and #8)
    - Ground truth is enriched at multiple levels (session, span) to ensure
      evaluators can access it regardless of SDK version
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union

from data import KNOWLEDGE_BASE
from tracing.tracer import Tracer
from utils.llm_clients import LLMClientFactory, AnthropicClient, OpenAIClient, extract_token_usage
from utils.prompts import get_prompt_builder, PromptBuilder

# Optional HoneyHive imports with graceful fallback
# If HoneyHive SDK is not installed, we provide no-op implementations
try:
    from honeyhive import trace, enrich_session, enrich_span
except ImportError:  # pragma: no cover - honeyhive optional
    # No-op decorators/functions for local development without HoneyHive
    def trace(func):  # type: ignore
        """No-op trace decorator when HoneyHive not available."""
        return func

    def enrich_session(**kwargs):  # type: ignore
        """No-op session enrichment when HoneyHive not available."""
        pass

    def enrich_span(**kwargs):  # type: ignore
        """No-op span enrichment when HoneyHive not available."""
        pass


class CustomerSupportAgent:
    """
    AI-powered customer support agent with three-step pipeline.

    This agent processes customer support tickets through a pipeline of:
    routing → retrieval → generation. Each step is traced for observability
    and can operate in either LLM mode (using Claude/GPT) or heuristic fallback
    mode (using rule-based logic).

    The agent is designed for experimentation and evaluation, with support for:
    - Multiple prompt versions (v1, v2)
    - Ground truth enrichment for evaluation
    - Token usage tracking
    - Comprehensive error handling
    - Multi-provider LLM support

    Attributes:
        api_key: API key for the LLM provider (optional)
        model: Model name to use (e.g., "claude-3-7-sonnet-20250219")
        tracer: Tracer instance for recording pipeline steps
        version: Agent version tag for experiment tracking
        prompt_version: Prompt template version (v1, v2)
        provider: LLM provider name ("anthropic" or "openai")
        client: LLM client instance (AnthropicClient or OpenAIClient)
        use_llm: Whether to use LLM or fall back to heuristics
        logger: Logger for debugging and monitoring
        prompt_builder: PromptBuilder for constructing prompts

    Example:
        >>> agent = CustomerSupportAgent(
        ...     model="claude-3-7-sonnet-20250219",
        ...     provider="anthropic",
        ...     version="v1",
        ... )
        >>> ticket = {"id": "123", "issue": "Can't upload files"}
        >>> result = agent.process_ticket(ticket)
        >>> print(result["output"]["answer"])
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
        prompt_version: str = "v1",
    ):
        """
        Initialize the customer support agent.

        Args:
            api_key: Optional API key for LLM provider. If not provided, will
                    check ANTHROPIC_API_KEY or OPENAI_API_KEY env vars
            model: LLM model name. Defaults to Claude 3.7 Sonnet
            tracer: Optional custom Tracer instance for recording steps
            version: Version tag for this agent (for experiment tracking)
            use_llm: Whether to use LLM calls. If None, auto-detects based on
                    whether client initialization succeeds
            logger: Optional logger instance for debugging
            provider: LLM provider ("anthropic" or "openai")
            prompt_version: Prompt template version to use ("v1" or "v2")

        Note:
            The agent will gracefully degrade to heuristic mode if:
            - No API key is provided
            - API key is invalid
            - LLM client initialization fails
            - use_llm is explicitly set to False
        """
        # Store configuration
        self.model = model
        self.tracer = tracer or Tracer()
        self.version = version or "v1"
        self.prompt_version = prompt_version
        self.provider = provider
        self.logger = logger or logging.getLogger(__name__)

        # Initialize prompt builder for this version
        self.prompt_builder = get_prompt_builder(version=prompt_version)

        # Initialize LLM client using factory
        # The factory handles provider-specific logic and error handling
        self.api_key = api_key or self._get_api_key_for_provider(provider)
        self.client: Optional[Union[AnthropicClient, OpenAIClient]] = None

        if self.api_key:
            # Auto-select appropriate model for OpenAI if using default Claude model
            selected_model = model
            if provider == "openai" and model == "claude-3-7-sonnet-20250219":
                selected_model = "gpt-4o-mini"
                self.model = selected_model

            # Create client using factory
            self.client = LLMClientFactory.create_client(
                provider=provider,
                api_key=self.api_key,
                model=selected_model,
                logger=self.logger,
            )

        # Determine if we should use LLM or heuristic mode
        # use_llm can be explicitly set, or auto-detected based on client availability
        if use_llm is not None:
            self.use_llm = use_llm
        else:
            self.use_llm = bool(self.client)

        # Ground truth storage for enrichment
        # This is set per-ticket in process_ticket() and used across all pipeline steps
        self._ground_truth: Optional[Dict[str, Any]] = None

        # Track current run/datapoint for metadata
        self._current_run_id: Optional[str] = None
        self._current_datapoint_id: Optional[str] = None

        self.logger.debug(
            f"CustomerSupportAgent initialized: provider={provider}, "
            f"model={self.model}, use_llm={self.use_llm}, version={self.version}"
        )

    def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """
        Get API key for the specified provider from environment.

        Args:
            provider: Provider name ("anthropic" or "openai")

        Returns:
            Optional[str]: API key if found, None otherwise
        """
        if provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        return None

    def _enrich_current_span(self) -> None:
        """
        Enrich the current HoneyHive span with ground truth feedback.

        This helper is called within traced functions to ensure ground truth
        data is attached to individual spans for evaluation. The ground truth
        is provided both as flat fields and nested under "ground_truth" key
        for compatibility with different evaluator implementations.

        Note:
            This is a no-op if no ground truth is set or if HoneyHive is not available.
        """
        if self._ground_truth:
            feedback_data = dict(self._ground_truth)
            feedback_data["ground_truth"] = self._ground_truth
            enrich_span(feedback=feedback_data, metadata={"ground_truth": self._ground_truth})

    def _heuristic_route(self, issue: str) -> Dict[str, Any]:
        """
        Deterministic heuristic routing based on keyword matching.

        This is a DEMO-SPECIFIC implementation that intentionally fails on
        ambiguous cases to demonstrate error cascades. In production, this
        would be more robust.

        **Intentional Limitations:**
        - Excludes "download" keyword (ambiguous - could be export or upload)
        - Excludes "cache" keyword (ambiguous - could be CDN or data)
        - This causes Issues #3 and #8 to fail routing, demonstrating how
          routing errors cascade through the pipeline

        Args:
            issue: Customer issue description text

        Returns:
            dict: Routing result with keys:
                - category: Predicted category
                - confidence: Float confidence score (0.6-0.82)
                - reasoning: Explanation of routing decision
                - raw_response: Metadata about routing mode
                - prompt_version: Prompt version used

        Note:
            The confidence scores are arbitrary but realistic-looking values
            for demo purposes. In production, these would come from a model.
        """
        text = issue.lower()

        # Intentionally simplified keyword matching that fails on ambiguous cases
        # This demonstrates the value of LLM-based routing vs. heuristics
        if any(k in text for k in ["upload", "404", "mixed content"]):
            category = "upload_errors"
        elif any(k in text for k in ["sso", "login", "reset", "2fa", "password", "locked"]):
            category = "account_access"
        elif any(k in text for k in ["export", "csv", "json", "queue"]):
            # NOTE: "download" is intentionally excluded - it's ambiguous!
            # This causes Issue #3 and #8 to fail routing (demo feature)
            category = "data_export"
        else:
            # Catch-all for unmatched issues
            category = "other"

        # Lower confidence for "other" category
        confidence = 0.82 if category != "other" else 0.6

        return {
            "category": category,
            "confidence": confidence,
            "reasoning": f"Rule-based routing matched keywords for {category}",
            "raw_response": {"mode": "heuristic"},
            "prompt_version": self.prompt_version,
        }

    @trace(event_name="route_to_category")  # type: ignore
    def route_to_category(self, issue: str) -> Dict[str, Any]:
        """
        Step 1: Route customer issue to appropriate support category.

        Uses LLM (if available) or heuristic fallback to categorize the issue
        into one of: upload_errors, account_access, data_export, other.

        This step is traced for observability and enriched with ground truth
        for evaluation purposes.

        Args:
            issue: Customer's issue description text

        Returns:
            dict: Routing result containing:
                - category: Predicted category
                - confidence: Float confidence score
                - reasoning: Explanation of routing decision
                - raw_response: Full LLM response or fallback metadata
                - prompt_version: Prompt version used

        Note:
            This method has a nested _run() function to separate the business
            logic from the tracing/logging logic. Ground truth enrichment happens
            before _run() executes to ensure it's captured in traces.

        Example:
            >>> agent = CustomerSupportAgent()
            >>> routing = agent.route_to_category("Can't upload files")
            >>> print(routing["category"])  # "upload_errors"
        """
        # Enrich this span with ground truth for evaluation
        # This ensures evaluators can access ground truth from traces
        if hasattr(self, '_ground_truth') and self._ground_truth:
            feedback_data = dict(self._ground_truth)
            feedback_data["ground_truth"] = self._ground_truth
            enrich_span(feedback=feedback_data)

        def _run() -> Dict[str, Any]:
            """Inner function containing routing logic."""
            # Use LLM if available and enabled
            if self.use_llm and self.client:
                try:
                    # Build prompt using prompt builder
                    prompt_data = self.prompt_builder.build_routing_prompt(issue)

                    # Make LLM call using client
                    response = self.client.chat_completion(
                        messages=prompt_data["messages"],
                        system=prompt_data["system"],
                        max_tokens=150,
                        temperature=0.0,
                    )

                    # Parse JSON response
                    try:
                        content = response["content"]
                        parsed = json.loads(content)

                        return {
                            "category": parsed.get("category", "other"),
                            "confidence": float(parsed.get("confidence", 0.5)),
                            "reasoning": parsed.get("reasoning", content),
                            "raw_response": response["raw_response"],
                            "prompt_version": self.prompt_version,
                        }

                    except (json.JSONDecodeError, KeyError, ValueError):
                        # LLM didn't return valid JSON, fall back to heuristic
                        self.logger.warning(
                            "Failed to parse LLM routing response, using heuristic",
                            extra={"content": response.get("content", "")},
                        )
                        output = self._heuristic_route(issue)
                        output["raw_response"] = {
                            "mode": "fallback_parse_error",
                            "content": response.get("content", ""),
                        }
                        return output

                except Exception as err:
                    # LLM call failed, fall back to heuristic
                    self.logger.warning(
                        f"LLM routing failed, falling back to heuristic: {err}",
                    )
                    output = self._heuristic_route(issue)
                    output["raw_response"] = {"mode": "fallback_on_error", "error": str(err)}
                    # Disable LLM for future calls in this session
                    self.use_llm = False
                    return output
            else:
                # LLM not available, use heuristic
                return self._heuristic_route(issue)

        # Execute routing logic
        output = _run()

        # Log routing result for debugging
        self.logger.debug(
            "route_to_category completed",
            extra={"issue": issue, "output": output},
        )

        # Extract token usage for tracking
        token_usage = extract_token_usage(
            output.get("raw_response"),
            fallback_input=len(issue.split()),
        )

        # Record this step in tracer for pipeline visibility
        self.tracer.record_step(
            "route_to_category",
            {"issue": issue},
            output,
            attributes={
                "predicted_category": output.get("category"),
                "confidence": output.get("confidence"),
                "token_usage": token_usage,
                "provider": self.provider,
                "model": self.model,
                "run_id": self._current_run_id,
                "datapoint_id": self._current_datapoint_id,
            },
        )

        return output

    @trace(event_name="retrieve_docs")  # type: ignore
    def retrieve_docs(self, category: str) -> Dict[str, Any]:
        """
        Step 2: Retrieve relevant documentation for the issue category.

        Looks up documentation snippets from the knowledge base for the given
        category. This is a simple dictionary lookup in the demo, but in
        production would be a vector database or semantic search.

        Args:
            category: Issue category from routing step

        Returns:
            dict: Retrieval result containing:
                - docs: List of documentation snippets
                - source: Where docs came from ("knowledge_base")
                - count: Number of docs retrieved
                - tokens: Estimated token count for docs

        Note:
            Token estimate is a simple word count approximation. In production,
            use proper tokenization for accuracy.

        Example:
            >>> agent = CustomerSupportAgent()
            >>> docs = agent.retrieve_docs("upload_errors")
            >>> print(docs["count"])  # Number of docs found
        """
        # Enrich this span with ground truth for evaluation
        if hasattr(self, '_ground_truth') and self._ground_truth:
            feedback_data = dict(self._ground_truth)
            feedback_data["ground_truth"] = self._ground_truth
            enrich_span(feedback=feedback_data)

        def _run() -> tuple[List[str], int]:
            """Inner function containing retrieval logic."""
            # Look up docs in knowledge base, with fallback to "other" category
            docs_local = KNOWLEDGE_BASE.get(category, KNOWLEDGE_BASE["other"])

            # Estimate token count (rough approximation: 1 token ≈ 1 word)
            token_estimate_local = sum(len(d.split()) for d in docs_local)

            return docs_local, token_estimate_local

        # Execute retrieval
        docs, token_estimate = _run()

        # Build output
        output = {
            "docs": docs,
            "source": "knowledge_base",
            "count": len(docs),
            "tokens": token_estimate,
        }

        # Log retrieval result
        self.logger.debug(
            "retrieve_docs completed",
            extra={"category": category, "count": len(docs)},
        )

        # Record this step in tracer
        self.tracer.record_step(
            "retrieve_docs",
            {"category": category},
            output,
            attributes={
                "token_usage": {"input": token_estimate, "output": 0},
                "provider": self.provider,
                "model": self.model,
                "run_id": self._current_run_id,
                "datapoint_id": self._current_datapoint_id,
            },
        )

        return output

    @staticmethod
    def _has_action_steps(text: str) -> bool:
        """
        Check if text contains numbered action steps.

        Args:
            text: Response text to check

        Returns:
            bool: True if text contains lines starting with "1.", "2.", etc.
        """
        return bool(re.search(r"^\s*\d+\.", text, re.MULTILINE))

    @staticmethod
    def _extract_steps(text: str) -> List[str]:
        """
        Extract numbered steps from response text.

        Args:
            text: Response text containing numbered steps

        Returns:
            list: List of step texts (without numbers)

        Example:
            >>> text = "1. First step\\n2. Second step"
            >>> steps = CustomerSupportAgent._extract_steps(text)
            >>> print(steps)  # ["First step", "Second step"]
        """
        lines = []
        for line in text.splitlines():
            # Check if line starts with a number and period
            if re.match(r"^\s*\d+\.", line.strip()):
                # Remove leading number and period
                cleaned = re.sub(r"^\s*\d+\.\s*", "", line).strip()
                lines.append(cleaned)
        return lines

    @trace(event_name="generate_response")  # type: ignore
    def generate_response(
        self,
        issue: str,
        docs: List[str],
        category: str | None = None,
    ) -> Dict[str, Any]:
        """
        Step 3: Generate personalized support response.

        Uses LLM (if available) or fallback template to create a helpful,
        actionable response to the customer's issue using the retrieved
        documentation as context.

        Args:
            issue: Customer's issue description
            docs: List of documentation snippets from retrieval step
            category: Optional category for fallback response context

        Returns:
            dict: Generation result containing:
                - category: Issue category
                - answer: The generated response text
                - steps: Extracted action steps from response
                - has_action_steps: Boolean whether response has numbered steps
                - tone: Response tone ("friendly_technical")
                - reasoning: Generation reasoning (if available from LLM)
                - safety_flags: Safety check results (pii, toxic)
                - raw_response: Full LLM response or fallback metadata
                - prompt_version: Prompt version used
                - token_usage: Token usage statistics

        Note:
            Safety flags are placeholders in this demo. In production, you'd
            run actual safety checks on the generated content.

        Example:
            >>> agent = CustomerSupportAgent()
            >>> response = agent.generate_response(
            ...     "Upload fails",
            ...     ["Check HTTPS", "Verify CDN"],
            ...     "upload_errors"
            ... )
            >>> print(response["answer"])  # Generated support response
        """
        # Enrich this span with ground truth for evaluation
        if hasattr(self, '_ground_truth') and self._ground_truth:
            feedback_data = dict(self._ground_truth)
            feedback_data["ground_truth"] = self._ground_truth
            enrich_span(feedback=feedback_data)

        def _run() -> tuple[str, str, Dict[str, Any], str]:
            """
            Inner function containing generation logic.

            Returns:
                tuple: (response_text, tone, raw_response, reasoning)
            """
            reasoning_text = ""

            # Use LLM if available and enabled
            if self.use_llm and self.client:
                try:
                    # Build prompt using prompt builder
                    prompt_data = self.prompt_builder.build_generation_prompt(issue, docs)

                    # Special handling for Anthropic to enable nested tracing
                    if self.provider == "anthropic":
                        # Wrap in traced function to ensure feedback propagates
                        @trace(event_name="anthropic.chat")  # type: ignore
                        def _call_anthropic():
                            # Enrich this specific span with feedback
                            self._enrich_current_span()
                            return self.client.chat_completion(  # type: ignore
                                messages=prompt_data["messages"],
                                system=prompt_data["system"],
                                max_tokens=350,
                                temperature=0.0,
                            )

                        response = _call_anthropic()
                    else:
                        # OpenAI or other provider
                        response = self.client.chat_completion(
                            messages=prompt_data["messages"],
                            system=prompt_data["system"],
                            max_tokens=350,
                            temperature=0.0,
                        )

                    # Extract response content
                    response_text = response["content"]
                    reasoning_text = response.get("reasoning", "")
                    tone = "friendly_technical"
                    raw = response["raw_response"]

                    return response_text, tone, raw, reasoning_text

                except Exception as err:
                    # LLM call failed, fall back to template
                    self.logger.warning(
                        f"LLM generation failed, using fallback template: {err}",
                    )
                    self.use_llm = False
                    response_text, tone, raw = self.prompt_builder.build_fallback_response(
                        issue, docs, category, err
                    )
                    return response_text, tone, raw, ""
            else:
                # LLM not available, use template
                response_text, tone, raw = self.prompt_builder.build_fallback_response(
                    issue, docs, category
                )
                return response_text, tone, raw, ""

        # Execute generation logic
        response_text, tone, raw, reasoning_text = _run()

        # Extract structured information from response
        has_action_steps = self._has_action_steps(response_text)
        extracted_steps = self._extract_steps(response_text) if has_action_steps else []

        # Calculate token usage
        token_usage = extract_token_usage(
            raw,
            fallback_input=sum(len(d.split()) for d in docs),
            fallback_output=len(response_text.split()),
        )

        # Build output
        output = {
            "category": category,
            "answer": response_text,
            "steps": extracted_steps,
            "has_action_steps": has_action_steps,
            "tone": tone or "friendly_technical",
            "reasoning": reasoning_text or ("generated" if self.use_llm else "templated_fallback"),
            "safety_flags": {"pii": False, "toxic": False},  # Placeholder for demo
            "raw_response": raw,
            "prompt_version": self.prompt_version,
            "token_usage": token_usage,
        }

        # Log generation result
        self.logger.debug(
            "generate_response completed",
            extra={
                "category": category,
                "has_action_steps": has_action_steps,
                "tone": tone,
            },
        )

        # Record this step in tracer
        self.tracer.record_step(
            "generate_response",
            {"issue": issue, "docs": docs},
            output,
            attributes={
                "category": category,
                "has_action_steps": has_action_steps,
                "token_usage": token_usage,
                "provider": self.provider,
                "model": self.model,
                "run_id": self._current_run_id,
                "datapoint_id": self._current_datapoint_id,
            },
        )

        return output

    def process_ticket(
        self,
        ticket: Dict[str, Any],
        run_id: str = "local-run",
        datapoint_id: Optional[str] = None,
        ground_truth: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a complete support ticket through the three-step pipeline.

        This is the main entry point for the agent. It orchestrates the full
        pipeline: routing → retrieval → generation, with comprehensive tracing
        and ground truth enrichment for evaluation.

        Args:
            ticket: Ticket dict with keys:
                - id: Ticket identifier
                - issue: Customer's issue description
                - customer: Optional customer identifier
            run_id: Experiment run identifier for grouping results
            datapoint_id: Optional datapoint ID (defaults to ticket ID)
            ground_truth: Optional ground truth data for evaluation with keys:
                - expected_category: Expected routing category
                - expected_keywords: List of keywords that should appear
                - expected_tone: Expected response tone
                - (other eval-specific fields)

        Returns:
            dict: Complete result containing:
                - ticket_id: Ticket identifier
                - datapoint_id: Datapoint identifier
                - run_id: Run identifier
                - prompt_version: Prompt version used
                - input: Original ticket data
                - steps: Dict with results from each step (route, retrieve, generate)
                - output: Formatted output with category, answer, steps, safety_flags
                - evaluations: Dict of evaluation results (populated by evaluators)
                - trace: Full trace data from tracer
                - version: Agent version

        Note:
            Ground truth is enriched at multiple levels:
            - Session level (enrich_session) for UI evaluators
            - Span level (enrich_span) for span-based evaluators
            - Instance level (self._ground_truth) for method access
            This redundancy ensures compatibility with different SDK versions.

        Example:
            >>> agent = CustomerSupportAgent()
            >>> ticket = {
            ...     "id": "123",
            ...     "issue": "Can't upload files",
            ...     "customer": "customer@example.com"
            ... }
            >>> ground_truth = {
            ...     "expected_category": "upload_errors",
            ...     "expected_keywords": ["HTTPS", "CDN"]
            ... }
            >>> result = agent.process_ticket(ticket, ground_truth=ground_truth)
            >>> print(result["output"]["category"])  # "upload_errors"
        """
        # Store ground truth on instance for access across all methods
        self._ground_truth = ground_truth

        # Store run/datapoint IDs for metadata
        self._current_run_id = run_id
        self._current_datapoint_id = datapoint_id or str(ticket["id"])

        # Start trace for this ticket
        self.tracer.start_trace(
            ticket_id=str(ticket["id"]),
            version=self.version,
            run_id=run_id,
            datapoint_id=datapoint_id or str(ticket["id"]),
            prompt_version=self.prompt_version,
            ground_truth=ground_truth,
        )

        # Enrich session with ground truth for UI evaluators
        # Provide both flat fields AND nested ground_truth for compatibility
        if ground_truth:
            feedback_data = dict(ground_truth)  # Copy all fields at flat level
            feedback_data["ground_truth"] = ground_truth  # Also nest under ground_truth key
            enrich_session(feedback=feedback_data)

        # Execute three-step pipeline
        routing = self.route_to_category(ticket["issue"])
        docs = self.retrieve_docs(routing["category"])
        response = self.generate_response(
            ticket["issue"],
            docs["docs"],
            category=routing["category"],
        )

        # End trace and get trace data
        trace = self.tracer.end_trace()

        # Build comprehensive result
        result = {
            "ticket_id": str(ticket["id"]),
            "datapoint_id": datapoint_id or str(ticket["id"]),
            "run_id": run_id,
            "prompt_version": self.prompt_version,
            "input": ticket,
            "steps": {
                "route": routing,
                "retrieve": docs,
                "generate": response,
            },
            "output": {
                "category": routing["category"],
                "answer": response["answer"],
                "steps": response["steps"],
                "safety_flags": response["safety_flags"],
            },
            "evaluations": {},  # Populated by external evaluators
            "trace": trace,
            "version": self.version,
        }

        # Log completion
        self.logger.debug(
            "process_ticket completed",
            extra={
                "ticket_id": ticket["id"],
                "category": routing["category"],
            },
        )

        return result
