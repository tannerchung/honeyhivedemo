"""
Tests for utils/honeyhive_init.py - HoneyHive initialization utilities
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from utils.honeyhive_init import (
    init_honeyhive_tracer,
    ensure_otlp_endpoint_set,
    get_honeyhive_config
)


class TestGetHoneyHiveConfig:
    """Test getting HoneyHive configuration."""

    @patch.dict(os.environ, {
        "HONEYHIVE_API_KEY": "test-key",
        "HONEYHIVE_PROJECT": "test-project",
        "HONEYHIVE_SOURCE": "test-source",
        "HONEYHIVE_SESSION": "test-session"
    })
    def test_get_config_from_env(self):
        """Test getting config from environment."""
        config = get_honeyhive_config()

        assert config["api_key"] == "test-key"
        assert config["project"] == "test-project"
        assert config["source"] == "test-source"
        assert "session_name" in config  # Generated or from env

    @patch.dict(os.environ, {}, clear=True)
    def test_get_config_with_defaults(self):
        """Test config uses defaults when env vars missing."""
        config = get_honeyhive_config()

        assert config["api_key"] is None
        assert config["project"] == "customer_support_demo"
        assert config["source"] == "dev"
        assert "session_name" in config


class TestEnsureOTLPEndpoint:
    """Test OTLP endpoint configuration."""

    @patch.dict(os.environ, {}, clear=True)
    def test_ensure_otlp_endpoint_sets_defaults(self):
        """Test OTLP endpoint sets default values when missing."""
        ensure_otlp_endpoint_set()

        expected_endpoint = "https://api.honeyhive.ai/opentelemetry/v1/traces"
        assert os.environ.get("HONEYHIVE_OTLP_ENDPOINT") == expected_endpoint
        assert os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") == expected_endpoint
        assert os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") == expected_endpoint

    @patch.dict(os.environ, {"HONEYHIVE_OTLP_ENDPOINT": "https://custom.endpoint/traces"})
    def test_ensure_otlp_endpoint_preserves_custom(self):
        """Test custom OTLP endpoint is preserved."""
        ensure_otlp_endpoint_set()

        assert os.environ.get("HONEYHIVE_OTLP_ENDPOINT") == "https://custom.endpoint/traces"

    @patch.dict(os.environ, {"HONEYHIVE_OTLP_ENDPOINT": ""})
    def test_ensure_otlp_endpoint_handles_empty_string(self):
        """Test empty string is replaced with default."""
        ensure_otlp_endpoint_set()

        expected_endpoint = "https://api.honeyhive.ai/opentelemetry/v1/traces"
        assert os.environ.get("HONEYHIVE_OTLP_ENDPOINT") == expected_endpoint

    @patch.dict(os.environ, {"HONEYHIVE_OTLP_ENDPOINT": "none"})
    def test_ensure_otlp_endpoint_handles_none_string(self):
        """Test 'none' string is replaced with default."""
        ensure_otlp_endpoint_set()

        expected_endpoint = "https://api.honeyhive.ai/opentelemetry/v1/traces"
        assert os.environ.get("HONEYHIVE_OTLP_ENDPOINT") == expected_endpoint


class TestInitHoneyHiveTracer:
    """Test HoneyHive tracer initialization."""

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key(self):
        """Test initialization without API key returns gracefully."""
        # Should not raise exception, just return without initializing
        init_honeyhive_tracer()
        # If we get here without exception, test passes

    @patch.dict(os.environ, {
        "HONEYHIVE_API_KEY": "test-key",
        "HONEYHIVE_PROJECT": "test-project"
    })
    @patch('utils.honeyhive_init.HoneyHiveTracer')
    def test_init_with_valid_config(self, mock_tracer):
        """Test initialization with valid configuration."""
        mock_instance = MagicMock()
        mock_tracer.init = MagicMock()

        init_honeyhive_tracer()

        # Should attempt to initialize tracer
        mock_tracer.init.assert_called_once()
        call_kwargs = mock_tracer.init.call_args[1]
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["project"] == "test-project"

    @patch.dict(os.environ, {"HONEYHIVE_API_KEY": "test-key"})
    @patch('utils.honeyhive_init.HoneyHiveTracer')
    def test_init_sets_session_name(self, mock_tracer):
        """Test initialization sets session name."""
        mock_instance = MagicMock()
        mock_tracer.init = MagicMock()

        init_honeyhive_tracer()

        call_kwargs = mock_tracer.init.call_args[1]
        assert "session_name" in call_kwargs
        assert call_kwargs["session_name"].startswith("Demo Session ")

    @patch.dict(os.environ, {"HONEYHIVE_API_KEY": "test-key"})
    @patch('utils.honeyhive_init.HoneyHiveTracer')
    def test_init_handles_import_error(self, mock_tracer):
        """Test graceful handling when HoneyHive SDK not available."""
        # Simulate import error
        with patch('utils.honeyhive_init.HoneyHiveTracer', side_effect=ImportError("No module")):
            # Should not raise, just log warning
            init_honeyhive_tracer()
            # If we get here, test passes

    @patch.dict(os.environ, {"HONEYHIVE_API_KEY": "test-key"})
    @patch('utils.honeyhive_init.HoneyHiveTracer')
    def test_init_raises_on_tracer_error(self, mock_tracer):
        """Test raises SystemExit when tracer init fails."""
        mock_tracer.init = MagicMock(side_effect=Exception("Init failed"))

        with pytest.raises(SystemExit):
            init_honeyhive_tracer()

    @patch.dict(os.environ, {
        "HONEYHIVE_API_KEY": "test-key",
        "HONEYHIVE_SOURCE": "production"
    })
    @patch('utils.honeyhive_init.HoneyHiveTracer')
    def test_init_uses_custom_source(self, mock_tracer):
        """Test initialization uses custom source from env."""
        mock_instance = MagicMock()
        mock_tracer.init = MagicMock()

        init_honeyhive_tracer()

        call_kwargs = mock_tracer.init.call_args[1]
        assert call_kwargs["source"] == "production"
