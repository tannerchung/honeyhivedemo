"""
Tests for utils/prompts.py - Prompt templates and builders
"""

import pytest
from utils.prompts import PromptTemplates, PromptBuilder


class TestPromptTemplates:
    """Test prompt template retrieval."""

    def test_get_routing_prompt_v1(self):
        """Test getting v1 routing prompt."""
        prompt = PromptTemplates.get_routing_prompt(version="v1")

        assert "Categorize the following customer support issue" in prompt
        assert "upload_errors" in prompt
        assert "account_access" in prompt
        assert "data_export" in prompt

    def test_get_response_prompt_v1(self):
        """Test getting v1 response generation prompt."""
        prompt = PromptTemplates.get_response_prompt(version="v1")

        assert "Generate a helpful support response" in prompt or "support response" in prompt.lower()
        assert "numbered steps" in prompt.lower() or "action steps" in prompt.lower()

    def test_get_fallback_response(self):
        """Test getting fallback response for category."""
        response = PromptTemplates.get_fallback_response("upload_errors")

        assert "upload" in response.lower()
        assert "1." in response  # Should have numbered steps

    def test_get_fallback_response_unknown_category(self):
        """Test fallback response for unknown category."""
        response = PromptTemplates.get_fallback_response("unknown_category")

        assert len(response) > 0  # Should return something
        assert "support" in response.lower() or "help" in response.lower()

    def test_invalid_version_returns_v1_default(self):
        """Test that invalid version falls back to v1."""
        prompt_v1 = PromptTemplates.get_routing_prompt(version="v1")
        prompt_invalid = PromptTemplates.get_routing_prompt(version="v999")

        # Should return v1 as fallback
        assert prompt_invalid == prompt_v1


class TestPromptBuilder:
    """Test prompt builder."""

    def test_prompt_builder_initialization(self):
        """Test PromptBuilder initializes with version."""
        builder = PromptBuilder(version="v1")

        assert builder.version == "v1"
        assert builder.templates is not None

    def test_build_routing_prompt(self):
        """Test building routing prompt with issue."""
        builder = PromptBuilder(version="v1")

        prompt = builder.build_routing_prompt(issue="My file upload is failing")

        assert "My file upload is failing" in prompt
        assert "Categorize" in prompt or "categorize" in prompt

    def test_build_response_prompt(self):
        """Test building response prompt with context."""
        builder = PromptBuilder(version="v1")

        docs = ["Doc 1: Upload troubleshooting", "Doc 2: Error codes"]
        prompt = builder.build_response_prompt(
            issue="Upload failing with 404",
            docs=docs,
            category="upload_errors"
        )

        assert "Upload failing with 404" in prompt
        assert "Doc 1" in prompt or "Upload troubleshooting" in prompt
        assert "upload_errors" in prompt or "upload" in prompt.lower()

    def test_build_response_prompt_with_empty_docs(self):
        """Test building response prompt with no docs."""
        builder = PromptBuilder(version="v1")

        prompt = builder.build_response_prompt(
            issue="Test issue",
            docs=[],
            category="other"
        )

        assert "Test issue" in prompt
        # Should still generate a valid prompt even without docs

    def test_get_fallback_from_builder(self):
        """Test getting fallback response through builder."""
        builder = PromptBuilder(version="v1")

        response = builder.get_fallback_response("account_access")

        assert "account" in response.lower() or "access" in response.lower() or "login" in response.lower()
        assert "1." in response  # Should have numbered steps

    def test_builder_version_consistency(self):
        """Test builder uses correct version throughout."""
        builder_v1 = PromptBuilder(version="v1")

        routing_v1 = builder_v1.build_routing_prompt("test")
        response_v1 = builder_v1.build_response_prompt("test", [], "other")

        # Both should be non-empty and contain version-appropriate content
        assert len(routing_v1) > 0
        assert len(response_v1) > 0
