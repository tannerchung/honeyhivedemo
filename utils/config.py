"""
Configuration management for the HoneyHive customer support demo.

This module handles environment variable loading, validation, and provides
a centralized configuration interface for the entire application. It ensures
that required API keys and settings are properly loaded and validated before
the application starts.

Key responsibilities:
- Load environment variables from .env files
- Validate required configuration values
- Provide default values for optional settings
- Ensure HoneyHive OTLP endpoint is properly configured
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """
    Application configuration settings.

    This class holds all configuration values needed by the customer support
    agent and related components. Values are loaded from environment variables
    with sensible defaults where appropriate.

    Attributes:
        anthropic_api_key: API key for Anthropic Claude models
        openai_api_key: API key for OpenAI models
        honeyhive_api_key: API key for HoneyHive tracing/experiments
        honeyhive_project: HoneyHive project name for organizing traces
        honeyhive_source: Source identifier for trace metadata (e.g., "dev", "prod")
        honeyhive_session: Optional session name override
        honeyhive_otlp_endpoint: OpenTelemetry endpoint for HoneyHive traces
        honeyhive_dataset_id: Optional managed dataset ID in HoneyHive
        default_model: Default LLM model to use
        default_provider: Default LLM provider ("anthropic" or "openai")
    """

    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    honeyhive_api_key: Optional[str] = None
    honeyhive_project: str = "customer_support_demo"
    honeyhive_source: str = "dev"
    honeyhive_session: Optional[str] = None
    honeyhive_otlp_endpoint: str = "https://api.honeyhive.ai/opentelemetry/v1/traces"
    honeyhive_dataset_id: Optional[str] = None
    default_model: str = "claude-3-7-sonnet-20250219"
    default_provider: str = "anthropic"

    @classmethod
    def from_env(cls) -> Config:
        """
        Load configuration from environment variables.

        This method loads the .env file if present and populates a Config
        object with values from environment variables. It also ensures that
        the HoneyHive OTLP endpoint is properly set in the environment for
        SDK auto-initialization.

        Returns:
            Config: A configured Config instance with values from environment

        Note:
            This method has a side effect of setting environment variables
            for OTLP endpoints to ensure HoneyHive SDK initialization works
            correctly. This is intentional to handle SDK auto-init behavior.
        """
        # Load .env file before reading environment variables
        load_dotenv()

        # Ensure HoneyHive OTLP endpoint is always set before any SDK auto-init
        # This is critical because some SDKs auto-initialize and need these set early
        default_otlp = "https://api.honeyhive.ai/opentelemetry/v1/traces"
        for var in ["HONEYHIVE_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT",
                    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]:
            val = os.getenv(var)
            # Set default if not present or if set to invalid placeholder values
            if not val or val.strip().lower() in ("none", "null", ""):
                os.environ[var] = default_otlp

        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            honeyhive_api_key=os.getenv("HONEYHIVE_API_KEY"),
            honeyhive_project=os.getenv("HONEYHIVE_PROJECT", "customer_support_demo"),
            honeyhive_source=os.getenv("HONEYHIVE_SOURCE", "dev"),
            honeyhive_session=os.getenv("HONEYHIVE_SESSION"),
            honeyhive_otlp_endpoint=os.getenv(
                "HONEYHIVE_OTLP_ENDPOINT",
                default_otlp
            ),
            honeyhive_dataset_id=os.getenv("HONEYHIVE_DATASET_ID"),
            default_model=os.getenv("DEFAULT_MODEL", "claude-3-7-sonnet-20250219"),
            default_provider=os.getenv("DEFAULT_PROVIDER", "anthropic"),
        )

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate that required configuration is present.

        Checks that at least one LLM provider API key is configured,
        allowing the application to run in either LLM mode or heuristic
        fallback mode.

        Returns:
            tuple[bool, list[str]]: A tuple of (is_valid, error_messages)
                - is_valid: True if configuration is valid
                - error_messages: List of validation error messages (empty if valid)

        Note:
            HoneyHive configuration is optional - the agent can run without it
            in local-only mode. At least one LLM API key is recommended but not
            required (heuristic mode works without LLM calls).
        """
        errors = []

        # At least one LLM provider should be configured (though not strictly required)
        if not self.anthropic_api_key and not self.openai_api_key:
            errors.append(
                "Warning: No LLM API keys configured. Agent will run in heuristic mode only."
            )

        # HoneyHive is optional but warn if partially configured
        if self.honeyhive_api_key and not self.honeyhive_project:
            errors.append(
                "Warning: HONEYHIVE_API_KEY set but HONEYHIVE_PROJECT is missing"
            )

        return len(errors) == 0, errors

    def get_provider_api_key(self, provider: str) -> Optional[str]:
        """
        Get the API key for a specific provider.

        Args:
            provider: The provider name ("anthropic" or "openai")

        Returns:
            Optional[str]: The API key for the provider, or None if not configured

        Raises:
            ValueError: If provider is not recognized
        """
        if provider == "anthropic":
            return self.anthropic_api_key
        elif provider == "openai":
            return self.openai_api_key
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def has_honeyhive_config(self) -> bool:
        """
        Check if HoneyHive is configured.

        Returns:
            bool: True if HoneyHive API key is present
        """
        return bool(self.honeyhive_api_key)


def load_config() -> Config:
    """
    Load and validate application configuration.

    This is the main entry point for loading configuration. It loads from
    environment variables and validates the result.

    Returns:
        Config: Validated configuration object

    Raises:
        SystemExit: If critical configuration is invalid (currently not raised,
                   but reserved for future strict validation)

    Example:
        >>> config = load_config()
        >>> if config.has_honeyhive_config():
        ...     print("HoneyHive tracing enabled")
    """
    config = Config.from_env()
    is_valid, errors = config.validate()

    # For now, we only warn on validation errors, don't fail
    # This allows the agent to run in heuristic mode without API keys
    if not is_valid:
        for error in errors:
            print(f"Config validation: {error}")

    return config
