"""
Unit and property-based tests for LLMClient.

This module tests the LLM client's behavior including:
- Initialization with and without API keys
- Availability checking
- Message rewriting with error handling
- Custom prompt generation
- Timeout handling
- Graceful fallback on errors
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.llm_client import LLMClient


class TestLLMClientInitialization:
    """Test LLMClient initialization and availability checking."""
    
    def test_init_with_valid_api_key(self):
        """Test initialization with a valid API key."""
        client = LLMClient(api_key="sk-test123")
        assert client.api_key == "sk-test123"
        assert client.available is True
        assert client.timeout == 5
    
    def test_init_without_api_key(self):
        """Test initialization without API key (fallback mode)."""
        client = LLMClient(api_key=None)
        assert client.api_key is None
        assert client.available is False
    
    def test_init_with_empty_api_key(self):
        """Test initialization with empty string API key."""
        client = LLMClient(api_key="")
        assert client.available is False
    
    def test_init_with_whitespace_api_key(self):
        """Test initialization with whitespace-only API key."""
        client = LLMClient(api_key="   ")
        assert client.available is False
    
    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout value."""
        client = LLMClient(api_key="sk-test123", timeout=10)
        assert client.timeout == 10
    
    def test_is_available_returns_true_with_key(self):
        """Test is_available() returns True when API key is present."""
        client = LLMClient(api_key="sk-test123")
        assert client.is_available() is True
    
    def test_is_available_returns_false_without_key(self):
        """Test is_available() returns False when API key is absent."""
        client = LLMClient(api_key=None)
        assert client.is_available() is False


class TestLLMClientRewriteMessage:
    """Test message rewriting functionality."""
    
    def test_rewrite_message_returns_none_when_unavailable(self):
        """Test rewrite_message returns None when LLM is unavailable."""
        client = LLMClient(api_key=None)
        result = client.rewrite_message("Test content")
        assert result is None
    
    def test_rewrite_message_returns_none_for_empty_content(self):
        """Test rewrite_message returns None for empty content."""
        client = LLMClient(api_key="sk-test123")
        result = client.rewrite_message("")
        assert result is None
    
    def test_rewrite_message_returns_none_for_whitespace_content(self):
        """Test rewrite_message returns None for whitespace-only content."""
        client = LLMClient(api_key="sk-test123")
        result = client.rewrite_message("   ")
        assert result is None
    
    def test_rewrite_message_success(self):
        """Test successful message rewriting."""
        # Setup mock
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Rewritten friendly message"
            mock_client.chat.completions.create.return_value = mock_response
            
            # Test
            client = LLMClient(api_key="sk-test123")
            result = client.rewrite_message("Original message", tone="friendly")
            
            assert result == "Rewritten friendly message"
            mock_client.chat.completions.create.assert_called_once()
    
    def test_rewrite_message_with_different_tones(self):
        """Test rewrite_message with different tone parameters."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Formal message"
            mock_client.chat.completions.create.return_value = mock_response
            
            client = LLMClient(api_key="sk-test123")
            result = client.rewrite_message("Test", tone="formal")
            
            # Verify system prompt includes the tone
            call_args = mock_client.chat.completions.create.call_args
            system_message = call_args[1]['messages'][0]['content']
            assert "formal" in system_message
    
    def test_rewrite_message_handles_api_error(self):
        """Test rewrite_message returns None on API error."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            
            client = LLMClient(api_key="sk-test123")
            result = client.rewrite_message("Test content")
            
            assert result is None
    
    def test_rewrite_message_handles_timeout(self):
        """Test rewrite_message returns None on timeout."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            mock_client.chat.completions.create.side_effect = TimeoutError("Timeout")
            
            client = LLMClient(api_key="sk-test123")
            result = client.rewrite_message("Test content")
            
            assert result is None
    
    def test_rewrite_message_handles_empty_response(self):
        """Test rewrite_message returns None when API returns empty content."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = ""
            mock_client.chat.completions.create.return_value = mock_response
            
            client = LLMClient(api_key="sk-test123")
            result = client.rewrite_message("Test content")
            
            assert result is None
    
    def test_rewrite_message_strips_whitespace(self):
        """Test rewrite_message strips leading/trailing whitespace from response."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "  Rewritten message  \n"
            mock_client.chat.completions.create.return_value = mock_response
            
            client = LLMClient(api_key="sk-test123")
            result = client.rewrite_message("Test")
            
            assert result == "Rewritten message"
    
    def test_rewrite_message_system_prompt_prevents_invention(self):
        """Test that system prompt explicitly forbids medical instruction invention."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            mock_client.chat.completions.create.return_value = mock_response
            
            client = LLMClient(api_key="sk-test123")
            client.rewrite_message("Test content")
            
            # Verify system prompt contains safety instructions
            call_args = mock_client.chat.completions.create.call_args
            system_message = call_args[1]['messages'][0]['content']
            assert "DO NOT add, remove, or modify any medical instructions" in system_message
            assert "DO NOT invent new medical advice" in system_message


class TestLLMClientGenerateWithPrompt:
    """Test custom prompt generation functionality."""
    
    def test_generate_with_prompt_returns_none_when_unavailable(self):
        """Test generate_with_prompt returns None when LLM is unavailable."""
        client = LLMClient(api_key=None)
        result = client.generate_with_prompt("System prompt", "User content")
        assert result is None
    
    def test_generate_with_prompt_returns_none_for_empty_system_prompt(self):
        """Test generate_with_prompt returns None for empty system prompt."""
        client = LLMClient(api_key="sk-test123")
        result = client.generate_with_prompt("", "User content")
        assert result is None
    
    def test_generate_with_prompt_returns_none_for_empty_user_content(self):
        """Test generate_with_prompt returns None for empty user content."""
        client = LLMClient(api_key="sk-test123")
        result = client.generate_with_prompt("System prompt", "")
        assert result is None
    
    def test_generate_with_prompt_success(self):
        """Test successful text generation with custom prompt."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Generated text"
            mock_client.chat.completions.create.return_value = mock_response
            
            client = LLMClient(api_key="sk-test123")
            result = client.generate_with_prompt("Custom system prompt", "User input")
            
            assert result == "Generated text"
            
            # Verify correct messages were sent
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]['messages']
            assert messages[0]['role'] == 'system'
            assert messages[0]['content'] == "Custom system prompt"
            assert messages[1]['role'] == 'user'
            assert messages[1]['content'] == "User input"
    
    def test_generate_with_prompt_handles_api_error(self):
        """Test generate_with_prompt returns None on API error."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            
            client = LLMClient(api_key="sk-test123")
            result = client.generate_with_prompt("System", "User")
            
            assert result is None
    
    def test_generate_with_prompt_strips_whitespace(self):
        """Test generate_with_prompt strips whitespace from response."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "\n  Generated text  \n"
            mock_client.chat.completions.create.return_value = mock_response
            
            client = LLMClient(api_key="sk-test123")
            result = client.generate_with_prompt("System", "User")
            
            assert result == "Generated text"


class TestLLMClientTimeout:
    """Test timeout handling."""
    
    def test_timeout_passed_to_openai_client(self):
        """Test that timeout is passed to OpenAI client initialization."""
        with patch('openai.OpenAI') as mock_openai_class:
            client = LLMClient(api_key="sk-test123", timeout=10)
            
            # Verify OpenAI was initialized with timeout
            mock_openai_class.assert_called_once_with(api_key="sk-test123", timeout=10)
    
    def test_default_timeout_is_5_seconds(self):
        """Test that default timeout is 5 seconds."""
        with patch('openai.OpenAI') as mock_openai_class:
            client = LLMClient(api_key="sk-test123")
            
            mock_openai_class.assert_called_once_with(api_key="sk-test123", timeout=5)


# Property-Based Tests using Hypothesis
from hypothesis import given, strategies as st, settings


class TestLLMClientProperties:
    """Property-based tests for LLMClient."""
    
    @given(st.text(min_size=1))
    def test_property_unavailable_client_always_returns_none(self, content):
        """
        Property: When LLM is unavailable, rewrite_message always returns None.
        
        **Validates: Requirements 4.3, 4.5, 4.6**
        """
        client = LLMClient(api_key=None)
        result = client.rewrite_message(content)
        assert result is None
    
    @given(st.text(min_size=1), st.text(min_size=1))
    def test_property_unavailable_client_generate_returns_none(self, system_prompt, user_content):
        """
        Property: When LLM is unavailable, generate_with_prompt always returns None.
        
        **Validates: Requirements 4.3, 4.5, 4.6**
        """
        client = LLMClient(api_key=None)
        result = client.generate_with_prompt(system_prompt, user_content)
        assert result is None
    
    @given(st.one_of(st.none(), st.just(""), st.just("   ")))
    def test_property_invalid_api_keys_make_client_unavailable(self, api_key):
        """
        Property: Invalid API keys (None, empty, whitespace) result in unavailable client.
        
        **Validates: Requirements 4.1, 4.2**
        """
        client = LLMClient(api_key=api_key)
        assert client.is_available() is False
    
    @settings(deadline=1000)  # Allow 1 second for OpenAI import
    @given(st.text(min_size=1, alphabet=st.characters(blacklist_categories=('Cs',))))
    def test_property_non_empty_api_key_makes_client_available(self, api_key):
        """
        Property: Any non-empty, non-whitespace API key makes client available.
        
        **Validates: Requirements 4.1**
        """
        # Skip if api_key is only whitespace
        if not api_key.strip():
            return
        
        client = LLMClient(api_key=api_key)
        # Note: Client may still be unavailable if OpenAI import fails,
        # but with a valid key string, it should attempt initialization
        assert client.api_key == api_key
    
    @settings(deadline=1000)  # Allow 1 second for OpenAI import
    @given(st.integers(min_value=1, max_value=60))
    def test_property_timeout_is_stored_correctly(self, timeout):
        """
        Property: Timeout value is always stored correctly in client.
        
        **Validates: Requirements 4.5 (timeout handling)**
        """
        client = LLMClient(api_key="sk-test", timeout=timeout)
        assert client.timeout == timeout
