"""
LLM client factory and management for the HoneyHive customer support demo.

This module provides a unified interface for creating and managing LLM clients
across different providers (Anthropic, OpenAI). It handles client initialization,
error handling, and provides a consistent API for making LLM calls regardless
of the underlying provider.

Key responsibilities:
- Create LLM clients for different providers
- Handle API key validation and client initialization errors
- Provide unified interface for LLM calls
- Extract token usage from different response formats
- Gracefully degrade to heuristic mode if LLM initialization fails
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Protocol, Union

# Optional imports - these may not be available in all environments
try:
    from anthropic import Anthropic
    from anthropic.types import Message as AnthropicMessage
except ImportError:  # pragma: no cover - optional dependency
    Anthropic = None  # type: ignore
    AnthropicMessage = None  # type: ignore

try:
    from openai import OpenAI
    from openai.types.chat import ChatCompletion as OpenAICompletion
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore
    OpenAICompletion = None  # type: ignore


class LLMClient(Protocol):
    """
    Protocol defining the interface for LLM clients.

    This protocol ensures that all LLM client implementations provide
    a consistent interface for making chat completion calls.
    """

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 150,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """
        Make a chat completion call to the LLM.

        Args:
            messages: List of message dictionaries with "role" and "content"
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            dict: Response containing "content", "raw_response", and "usage"
        """
        ...


class AnthropicClient:
    """
    Wrapper for Anthropic Claude API client.

    This class provides a consistent interface for making calls to Anthropic's
    Claude models, handling response parsing and token usage extraction.

    Attributes:
        client: The underlying Anthropic API client
        model: The Claude model to use (e.g., "claude-3-7-sonnet-20250219")
        logger: Logger for debugging and error tracking
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-7-sonnet-20250219",
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Claude model name
            logger: Optional logger for debugging

        Raises:
            ImportError: If anthropic package is not installed
            Exception: If client initialization fails
        """
        if Anthropic is None:
            raise ImportError("anthropic package is not installed")

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.logger = logger or logging.getLogger(__name__)

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 150,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """
        Make a chat completion call to Claude.

        Args:
            messages: List of message dicts with "role" and "content" keys
            system: Optional system prompt to guide Claude's behavior
            max_tokens: Maximum tokens to generate in response
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            dict: Response containing:
                - content: The generated text content
                - raw_response: Full API response object
                - usage: Token usage statistics

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else "",
                messages=messages,
            )

            # Extract content from response
            content = response.content[0].text if hasattr(response, "content") else ""

            # Get token usage
            usage = self._extract_token_usage(response)

            return {
                "content": content,
                "raw_response": response.model_dump() if hasattr(response, "model_dump") else str(response),
                "usage": usage,
            }

        except Exception as err:
            self.logger.error(f"Anthropic API call failed: {err}")
            raise

    def _extract_token_usage(self, response: Any) -> Dict[str, int]:
        """
        Extract token usage from Anthropic response.

        Args:
            response: Anthropic API response object

        Returns:
            dict: Token usage with "input" and "output" keys
        """
        if hasattr(response, "usage"):
            usage_obj = response.usage
            try:
                # Try to convert to dict
                return usage_obj.model_dump()
            except Exception:
                # Fallback to dict conversion
                try:
                    return dict(usage_obj)
                except Exception:
                    return {"input": 0, "output": 0}
        return {"input": 0, "output": 0}


class OpenAIClient:
    """
    Wrapper for OpenAI API client.

    This class provides a consistent interface for making calls to OpenAI's
    models, handling response parsing and token usage extraction.

    Attributes:
        client: The underlying OpenAI API client
        model: The OpenAI model to use (e.g., "gpt-4o-mini")
        logger: Logger for debugging and error tracking
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: OpenAI model name
            logger: Optional logger for debugging

        Raises:
            ImportError: If openai package is not installed
            Exception: If client initialization fails
        """
        if OpenAI is None:
            raise ImportError("openai package is not installed")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.logger = logger or logging.getLogger(__name__)

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 150,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """
        Make a chat completion call to OpenAI.

        Args:
            messages: List of message dicts with "role" and "content" keys
            system: Optional system prompt (will be prepended to messages)
            max_tokens: Maximum tokens to generate in response
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            dict: Response containing:
                - content: The generated text content
                - raw_response: Full API response object
                - usage: Token usage statistics
                - reasoning: Optional reasoning text (for models that support it)

        Raises:
            Exception: If API call fails
        """
        try:
            # OpenAI expects system message as first message
            all_messages = []
            if system:
                all_messages.append({"role": "system", "content": system})
            all_messages.extend(messages)

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=all_messages,
            )

            # Extract content from response
            choice = response.choices[0]
            content = choice.message.content or ""

            # Extract reasoning if available (for reasoning models)
            reasoning = ""
            if hasattr(choice.message, "reasoning"):
                reasoning = choice.message.reasoning or ""

            # Get token usage
            usage = self._extract_token_usage(response)

            return {
                "content": content,
                "reasoning": reasoning,
                "raw_response": response.model_dump() if hasattr(response, "model_dump") else str(response),
                "usage": usage,
            }

        except Exception as err:
            self.logger.error(f"OpenAI API call failed: {err}")
            raise

    def _extract_token_usage(self, response: Any) -> Dict[str, int]:
        """
        Extract token usage from OpenAI response.

        Args:
            response: OpenAI API response object

        Returns:
            dict: Token usage with "input" and "output" keys
        """
        if hasattr(response, "usage"):
            usage_obj = response.usage
            try:
                # OpenAI uses prompt_tokens and completion_tokens
                return usage_obj.model_dump()
            except Exception:
                # Fallback to dict conversion
                try:
                    return dict(usage_obj)
                except Exception:
                    return {"input": 0, "output": 0}
        return {"input": 0, "output": 0}


class LLMClientFactory:
    """
    Factory for creating LLM clients.

    This class centralizes the logic for creating LLM clients for different
    providers, handling initialization errors, and selecting appropriate models.

    The factory pattern allows for:
    - Consistent client creation across the application
    - Centralized error handling for missing API keys or packages
    - Easy addition of new providers in the future
    - Graceful degradation to heuristic mode when LLM setup fails
    """

    @staticmethod
    def create_client(
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> Optional[Union[AnthropicClient, OpenAIClient]]:
        """
        Create an LLM client for the specified provider.

        This method handles all the complexity of client initialization:
        - Validates API keys are present
        - Selects appropriate default models per provider
        - Handles missing dependencies gracefully
        - Logs errors for debugging

        Args:
            provider: Provider name ("anthropic" or "openai")
            api_key: Optional API key (if not provided, will return None)
            model: Optional model name (uses provider default if not specified)
            logger: Optional logger for error reporting

        Returns:
            LLMClient implementation or None if client cannot be created

        Note:
            Returning None is intentional - it allows the agent to fall back
            to heuristic mode when LLM clients cannot be initialized.

        Example:
            >>> factory = LLMClientFactory()
            >>> client = factory.create_client("anthropic", api_key="sk-...")
            >>> if client:
            ...     response = client.chat_completion([{"role": "user", "content": "Hi"}])
        """
        logger = logger or logging.getLogger(__name__)

        # No API key means no client
        if not api_key:
            logger.warning(f"No API key provided for {provider}, client will be None")
            return None

        try:
            if provider == "anthropic":
                # Default to Claude 3.7 Sonnet if no model specified
                default_model = "claude-3-7-sonnet-20250219"
                selected_model = model or default_model
                return AnthropicClient(
                    api_key=api_key,
                    model=selected_model,
                    logger=logger,
                )

            elif provider == "openai":
                # Default to GPT-4o-mini if no model specified
                default_model = "gpt-4o-mini"
                selected_model = model or default_model
                return OpenAIClient(
                    api_key=api_key,
                    model=selected_model,
                    logger=logger,
                )

            else:
                logger.error(f"Unknown provider: {provider}")
                return None

        except ImportError as err:
            logger.warning(
                f"{provider} SDK not available, falling back to heuristic mode",
                extra={"error": str(err)},
            )
            return None

        except Exception as err:
            logger.warning(
                f"Failed to initialize {provider} client, falling back to heuristic mode",
                extra={"error": str(err)},
            )
            return None


def extract_token_usage(
    raw_response: Any,
    fallback_input: int = 0,
    fallback_output: int = 0,
) -> Dict[str, int]:
    """
    Extract token usage from any LLM response format.

    This utility function handles token usage extraction from various response
    formats (Anthropic, OpenAI, or raw dicts). It provides a unified interface
    for getting token counts regardless of the underlying provider.

    Args:
        raw_response: The raw LLM API response (any format)
        fallback_input: Fallback input token count if extraction fails
        fallback_output: Fallback output token count if extraction fails

    Returns:
        dict: Token usage with "input" and "output" keys (or provider-specific keys)

    Note:
        This function is defensive and will always return a valid dict with
        numeric values, using fallbacks when extraction fails. This ensures
        token tracking doesn't break the application flow.

    Example:
        >>> usage = extract_token_usage(anthropic_response)
        >>> print(f"Used {usage['input']} input tokens")
    """
    # Check if it's a dict with usage key
    if isinstance(raw_response, dict) and "usage" in raw_response:
        return raw_response.get("usage", {})

    # Check if it's an object with usage attribute
    if hasattr(raw_response, "usage"):
        usage_obj = getattr(raw_response, "usage")
        try:
            # Try model_dump() for Pydantic models
            return usage_obj.model_dump()
        except Exception:
            try:
                # Try dict conversion
                return dict(usage_obj)
            except Exception:
                # Fallback to default values
                return {"input": fallback_input, "output": fallback_output}

    # No usage information found, use fallbacks
    return {"input": fallback_input, "output": fallback_output}
