"""
Tests for utils/config.py - Configuration management
"""

import os
import pytest
from unittest.mock import patch
from utils.config import Config, load_config


class TestConfig:
    """Test Config dataclass and utilities."""

    def test_config_dataclass_defaults(self):
        """Test Config dataclass has sensible defaults."""
        config = Config()

        assert config.anthropic_api_key is None
        assert config.openai_api_key is None
        assert config.honeyhive_api_key is None
        assert config.honeyhive_project == "customer_support_demo"
        assert config.honeyhive_source == "dev"
        assert config.environment == "development"
        assert config.debug is False

    def test_config_with_custom_values(self):
        """Test Config dataclass accepts custom values."""
        config = Config(
            anthropic_api_key="test-key",
            honeyhive_project="test-project",
            debug=True
        )

        assert config.anthropic_api_key == "test-key"
        assert config.honeyhive_project == "test-project"
        assert config.debug is True

    @patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "OPENAI_API_KEY": "test-openai-key",
        "HONEYHIVE_API_KEY": "test-honeyhive-key",
        "HONEYHIVE_PROJECT": "test-project",
        "DEBUG": "True"
    }, clear=True)
    def test_load_config_from_env(self):
        """Test loading config from environment variables."""
        config = load_config()

        assert config.anthropic_api_key == "test-anthropic-key"
        assert config.openai_api_key == "test-openai-key"
        assert config.honeyhive_api_key == "test-honeyhive-key"
        assert config.honeyhive_project == "test-project"
        assert config.debug is True

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_with_missing_keys(self):
        """Test loading config when env vars are missing uses defaults."""
        config = load_config()

        assert config.anthropic_api_key is None
        assert config.honeyhive_project == "customer_support_demo"
        assert config.debug is False

    @patch.dict(os.environ, {
        "DEBUG": "false",
        "HONEYHIVE_PROJECT": ""
    }, clear=True)
    def test_load_config_handles_empty_strings(self):
        """Test empty string env vars are treated as None/defaults."""
        config = load_config()

        assert config.debug is False
        # Empty project string should use default
        assert config.honeyhive_project == "customer_support_demo"

    def test_config_otlp_endpoint_default(self):
        """Test OTLP endpoint has correct default."""
        config = Config()
        assert config.honeyhive_otlp_endpoint == "https://api.honeyhive.ai/opentelemetry/v1/traces"

    @patch.dict(os.environ, {
        "HONEYHIVE_OTLP_ENDPOINT": "https://custom.endpoint/traces"
    }, clear=True)
    def test_config_custom_otlp_endpoint(self):
        """Test custom OTLP endpoint can be set."""
        config = load_config()
        assert config.honeyhive_otlp_endpoint == "https://custom.endpoint/traces"
