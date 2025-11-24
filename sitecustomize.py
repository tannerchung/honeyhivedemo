"""
Ensure HoneyHive OTLP endpoints are set as early as possible, before any SDK auto-init.
"""

import os
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Force OTLP endpoints to a valid URL before any SDK auto-init, even if set to "None"
default_traces = "https://api.honeyhive.ai/opentelemetry/v1/traces"

def _normalize(var: str, default: str) -> None:
    val = os.getenv(var)
    if not val or val.strip().lower() in ("none", "null", ""):
        os.environ[var] = default

_normalize("HONEYHIVE_OTLP_ENDPOINT", default_traces)
_normalize("OTEL_EXPORTER_OTLP_ENDPOINT", default_traces)
_normalize("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", default_traces)
_normalize("OTEL_METRICS_EXPORTER", "none")
