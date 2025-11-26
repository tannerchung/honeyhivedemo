"""
HoneyHive tracer initialization for the customer support demo.

This module handles the setup and initialization of the HoneyHive tracing SDK.
It's extracted from the main CLI entrypoint to:
- Centralize HoneyHive configuration logic
- Make it reusable across different entrypoints
- Simplify testing and debugging
- Keep the main() function focused on application flow

Key responsibilities:
- Initialize HoneyHive tracer with proper configuration
- Validate required environment variables (API key, project)
- Handle initialization errors gracefully
- Set up OpenTelemetry endpoints correctly
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Optional


def init_honeyhive_tracer(
    api_key: Optional[str] = None,
    project: Optional[str] = None,
    source: Optional[str] = None,
    session_name: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """
    Initialize HoneyHive tracer if SDK and configuration are available.

    This function sets up the HoneyHive tracing SDK for the application,
    enabling trace collection and export to the HoneyHive platform. It
    handles all aspects of initialization including:
    - Validating API key is present
    - Setting OpenTelemetry endpoints
    - Generating session names
    - Error handling and logging

    Args:
        api_key: HoneyHive API key (defaults to HONEYHIVE_API_KEY env var)
        project: HoneyHive project name (defaults to HONEYHIVE_PROJECT env var)
        source: Source identifier for traces (defaults to HONEYHIVE_SOURCE env var)
        session_name: Optional session name (defaults to generated name)
        logger: Optional logger for status messages

    Returns:
        bool: True if initialization succeeded, False otherwise

    Raises:
        SystemExit: If initialization fails critically (API key present but init fails)

    Note:
        This function will exit the process if HoneyHive initialization fails
        when an API key is present. This is intentional to avoid running
        partial experiments that won't be properly tracked. For local development
        without HoneyHive, simply don't set HONEYHIVE_API_KEY.

    Example:
        >>> # Initialize with defaults from environment
        >>> success = init_honeyhive_tracer()
        >>> if success:
        ...     print("HoneyHive tracing enabled")

        >>> # Initialize with explicit configuration
        >>> init_honeyhive_tracer(
        ...     api_key="hh-...",
        ...     project="my_project",
        ...     source="production",
        ...     session_name="Session 123"
        ... )
    """
    logger = logger or logging.getLogger(__name__)

    # Load configuration from environment if not provided
    api_key = api_key or os.getenv("HONEYHIVE_API_KEY")
    project = project or os.getenv("HONEYHIVE_PROJECT", "customer_support_demo")
    source = source or os.getenv("HONEYHIVE_SOURCE", "dev")

    # Generate session name if not provided
    # Check for environment override first
    session_env = os.getenv("HONEYHIVE_SESSION")
    if session_name is None:
        session_name = session_env if session_env else f"Demo Session {uuid.uuid4().hex[:6]}"

    # Ensure OTLP endpoint is set before SDK initialization
    # The SDK auto-initializes on import and needs this set early
    otlp_endpoint = os.getenv(
        "HONEYHIVE_OTLP_ENDPOINT",
        "https://api.honeyhive.ai/opentelemetry/v1/traces",
    )
    os.environ["HONEYHIVE_OTLP_ENDPOINT"] = otlp_endpoint

    # If no API key, skip initialization (local mode)
    if not api_key:
        logger.info("No HONEYHIVE_API_KEY found, running in local mode without tracing")
        return False

    # Try to import HoneyHive SDK
    try:
        from honeyhive import HoneyHiveTracer
    except ImportError as err:
        logger.warning(
            "HoneyHive SDK not available (install with: pip install honeyhive)",
            extra={"error": str(err)},
        )
        return False

    # Initialize the tracer
    try:
        HoneyHiveTracer.init(
            api_key=api_key,
            project=project,
            source=source,
            session_name=session_name,
        )

        logger.info(
            "HoneyHive tracer initialized successfully",
            extra={
                "project": project,
                "source": source,
                "session": session_name,
                "endpoint": otlp_endpoint,
            },
        )

        return True

    except Exception as err:
        # Hard exit to avoid noisy partial runs when API key is present
        # This ensures we don't run experiments that won't be tracked
        logger.error(
            "HoneyHive tracer initialization failed; exiting to avoid partial runs",
            extra={"error": str(err)},
        )
        raise SystemExit(f"HoneyHive tracer init failed: {err}")


def ensure_otlp_endpoint_set() -> None:
    """
    Ensure HoneyHive OTLP endpoint is set in environment.

    This function must be called BEFORE any SDK imports that might
    auto-initialize OpenTelemetry. It sets the OTLP endpoint environment
    variables to ensure traces are sent to HoneyHive.

    This is separated from init_honeyhive_tracer() because it needs to
    run very early in the application lifecycle, before any imports that
    might trigger SDK auto-initialization.

    Side Effects:
        Sets HONEYHIVE_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_ENDPOINT, and
        OTEL_EXPORTER_OTLP_TRACES_ENDPOINT environment variables if they're
        not already set or are set to invalid placeholder values.

    Note:
        This function has intentional side effects on environment variables.
        It's designed to be called once at application startup before SDK
        initialization occurs.

    Example:
        >>> # Call this at the top of your main module
        >>> ensure_otlp_endpoint_set()
        >>> # Now safe to import SDKs that auto-initialize
        >>> from honeyhive import HoneyHiveTracer
    """
    default_otlp = "https://api.honeyhive.ai/opentelemetry/v1/traces"

    # List of environment variables that control OTLP endpoint
    # Different SDKs may check different variables, so we set all of them
    otlp_vars = [
        "HONEYHIVE_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    ]

    for var in otlp_vars:
        val = os.getenv(var)
        # Set default if not present or if set to invalid placeholder values
        # Some users may set these to "none" or "null" to disable, but we want
        # to ensure HoneyHive tracing works by default
        if not val or val.strip().lower() in ("none", "null", ""):
            os.environ[var] = default_otlp


def get_honeyhive_config() -> dict[str, Optional[str]]:
    """
    Get current HoneyHive configuration from environment.

    This is a utility function for debugging and logging to see what
    HoneyHive configuration is active.

    Returns:
        dict: Configuration values from environment
            - api_key_set: Whether API key is configured (bool, not the actual key)
            - project: Project name
            - source: Source identifier
            - session: Session name if set
            - otlp_endpoint: OpenTelemetry endpoint URL
            - dataset_id: Dataset ID if configured

    Example:
        >>> config = get_honeyhive_config()
        >>> print(f"Project: {config['project']}")
        >>> print(f"API key configured: {config['api_key_set']}")
    """
    api_key = os.getenv("HONEYHIVE_API_KEY")

    return {
        "api_key_set": bool(api_key),  # Don't expose actual key
        "project": os.getenv("HONEYHIVE_PROJECT", "customer_support_demo"),
        "source": os.getenv("HONEYHIVE_SOURCE", "dev"),
        "session": os.getenv("HONEYHIVE_SESSION"),
        "otlp_endpoint": os.getenv(
            "HONEYHIVE_OTLP_ENDPOINT",
            "https://api.honeyhive.ai/opentelemetry/v1/traces",
        ),
        "dataset_id": os.getenv("HONEYHIVE_DATASET_ID"),
    }
