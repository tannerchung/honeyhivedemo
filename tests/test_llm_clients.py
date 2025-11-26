"""
Tests for utils/llm_clients.py - LLM client factory and wrappers
"""

import pytest
from unittest.mock import Mock, patch
from utils.llm_clients import LLMClientFactory, AnthropicClient, OpenAIClient


class TestLLMClientFactory:
    """Test LLM client factory."""

    def test_factory_creates_anthropic_client(self):
        """Test factory creates Anthropic client."""
        with patch('utils.llm_clients.Anthropic') as mock_anthropic:
            mock_instance = Mock()
            mock_anthropic.return_value = mock_instance

            client = LLMClientFactory.create_client(
                provider="anthropic",
                api_key="test-key",
                model="claude-3-5-sonnet"
            )

            assert isinstance(client, AnthropicClient)
            mock_anthropic.assert_called_once_with(api_key="test-key")

    def test_factory_creates_openai_client(self):
        """Test factory creates OpenAI client."""
        with patch('utils.llm_clients.OpenAI') as mock_openai:
            mock_instance = Mock()
            mock_openai.return_value = mock_instance

            client = LLMClientFactory.create_client(
                provider="openai",
                api_key="test-key",
                model="gpt-4o-mini"
            )

            assert isinstance(client, OpenAIClient)
            mock_openai.assert_called_once_with(api_key="test-key")

    def test_factory_returns_none_for_invalid_provider(self):
        """Test factory returns None for invalid provider."""
        client = LLMClientFactory.create_client(
            provider="invalid",
            api_key="test-key"
        )

        assert client is None

    def test_factory_returns_none_without_api_key(self):
        """Test factory returns None when API key is missing."""
        client = LLMClientFactory.create_client(
            provider="anthropic",
            api_key=None
        )

        assert client is None


class TestAnthropicClient:
    """Test Anthropic client wrapper."""

    def test_anthropic_client_initialization(self):
        """Test Anthropic client initializes correctly."""
        with patch('utils.llm_clients.Anthropic') as mock_anthropic:
            mock_instance = Mock()
            mock_anthropic.return_value = mock_instance

            client = AnthropicClient(api_key="test-key", model="claude-3-5-sonnet")

            assert client.client == mock_instance
            assert client.model == "claude-3-5-sonnet"
            assert client.provider == "anthropic"

    def test_anthropic_client_generate_with_json_response(self):
        """Test Anthropic client generates response with JSON parsing."""
        with patch('utils.llm_clients.Anthropic') as mock_anthropic:
            # Mock the Anthropic response
            mock_content = Mock()
            mock_content.text = '{"category": "test", "confidence": 0.9}'
            mock_message = Mock()
            mock_message.content = [mock_content]
            mock_message.usage = Mock(input_tokens=10, output_tokens=5)

            mock_instance = Mock()
            mock_instance.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_instance

            client = AnthropicClient(api_key="test-key")

            response, tokens = client.generate(
                prompt="test prompt",
                response_format="json"
            )

            assert response == {"category": "test", "confidence": 0.9}
            assert tokens == {"input_tokens": 10, "output_tokens": 5}


class TestOpenAIClient:
    """Test OpenAI client wrapper."""

    def test_openai_client_initialization(self):
        """Test OpenAI client initializes correctly."""
        with patch('utils.llm_clients.OpenAI') as mock_openai:
            mock_instance = Mock()
            mock_openai.return_value = mock_instance

            client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")

            assert client.client == mock_instance
            assert client.model == "gpt-4o-mini"
            assert client.provider == "openai"

    def test_openai_client_generate_with_json_response(self):
        """Test OpenAI client generates response with JSON parsing."""
        with patch('utils.llm_clients.OpenAI') as mock_openai:
            # Mock the OpenAI response
            mock_message = Mock()
            mock_message.content = '{"category": "test", "confidence": 0.9}'
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5)

            mock_instance = Mock()
            mock_instance.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_instance

            client = OpenAIClient(api_key="test-key")

            response, tokens = client.generate(
                prompt="test prompt",
                response_format="json"
            )

            assert response == {"category": "test", "confidence": 0.9}
            assert tokens == {"input_tokens": 10, "output_tokens": 5}

    def test_client_handles_non_json_response(self):
        """Test client handles non-JSON response gracefully."""
        with patch('utils.llm_clients.Anthropic') as mock_anthropic:
            mock_content = Mock()
            mock_content.text = "plain text response"
            mock_message = Mock()
            mock_message.content = [mock_content]
            mock_message.usage = Mock(input_tokens=10, output_tokens=5)

            mock_instance = Mock()
            mock_instance.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_instance

            client = AnthropicClient(api_key="test-key")

            response, tokens = client.generate(
                prompt="test prompt",
                response_format="text"
            )

            assert response == "plain text response"
            assert tokens == {"input_tokens": 10, "output_tokens": 5}
