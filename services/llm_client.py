"""
LLM Client for OpenRouter API integration with graceful fallback.

This module provides a safe interface to OpenRouter's API for message rewriting.
Uses a 4-tier fallback system with free models:
1. google/gemma-4-31b-it:free (Primary)
2. google/gemma-4-26b-a4b-it:free (Fallback 1)
3. nvidia/nemotron-3-super-120b-a12b:free (Fallback 2)
4. meta-llama/llama-3.3-70b-instruct:free (Fallback 3)
5. Template-based responses (Final fallback)

The client handles API failures gracefully by returning None, allowing the
system to fall back to template-based message generation.

Key Safety Features:
- Timeout handling (5 seconds) for all API calls
- Four-tier model fallback chain
- Graceful error handling with None returns
- System prompts that prevent medical instruction invention
- Availability checking before API calls
- Free model usage (no costs)
"""

from typing import Optional
import os


class LLMClient:
    """
    Interface to OpenRouter API with graceful fallback.
    
    The LLM client manages connections to OpenRouter's API and provides methods
    for message rewriting and generation. Uses a 4-tier fallback system with
    free models, automatically trying each model in sequence until one succeeds.
    All methods handle errors gracefully and return None on failure, allowing 
    the system to fall back to template-based generation.
    
    Attributes:
        api_key: OpenRouter API key (None if unavailable)
        available: Boolean indicating if LLM is available for use
        timeout: Timeout in seconds for API calls (default: 5)
        models: List of models to try in order (4-tier fallback)
    """
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 60,
                 models: Optional[list] = None):
        """
        Initialize LLM client with optional API key.
        
        Args:
            api_key: OpenRouter API key. If None, client operates in fallback mode.
            timeout: Timeout in seconds for API calls (default: 5)
            models: List of models to try in order. If None, uses default 4-tier fallback:
                   1. google/gemma-4-31b-it:free
                   2. google/gemma-4-26b-a4b-it:free
                   3. nvidia/nemotron-3-super-120b-a12b:free
                   4. meta-llama/llama-3.3-70b-instruct:free
        
        Postconditions:
            - self.available is True if api_key is not None and not empty
            - self.available is False if api_key is None or empty
            - self.timeout is set to provided value
            - self.models is set to provided list or default fallback chain
        """
        self.api_key = api_key
        self.available = api_key is not None and api_key.strip() != ""
        self.timeout = timeout
        
        # Default 4-tier fallback chain
        if models is None:
            self.models = [
                "google/gemma-4-31b-it:free",
                "google/gemma-4-26b-a4b-it:free",
                "nvidia/nemotron-3-super-120b-a12b:free",
                "meta-llama/llama-3.3-70b-instruct:free"
            ]
        else:
            self.models = models
        
        self._client = None
        
        # Initialize OpenAI-compatible client for OpenRouter if API key is available
        if self.available:
            try:
                from openai import OpenAI
                # OpenRouter uses OpenAI-compatible API
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://openrouter.ai/api/v1",
                    timeout=self.timeout
                )
            except Exception:
                # If OpenAI import or initialization fails, mark as unavailable
                self.available = False
                self._client = None
    
    def is_available(self) -> bool:
        """
        Check if LLM is available for use.
        
        Returns:
            True if API key is present and client is initialized, False otherwise
        
        Postconditions:
            - Returns True if and only if self.available is True
            - No side effects
        """
        return self.available
    
    def rewrite_message(self, structured_content: str, tone: str = "friendly") -> Optional[str]:
        """
        Rewrite structured content in specified tone using LLM.
        
        This method takes structured appointment preparation content and rewrites
        it in a more human-friendly tone. The system prompt explicitly forbids
        inventing medical instructions.
        
        Args:
            structured_content: The structured message content to rewrite
            tone: Desired tone ("friendly", "formal", or "concise")
        
        Returns:
            Rewritten message string if successful, None if LLM unavailable or call fails
        
        Preconditions:
            - structured_content is a non-empty string
            - tone is one of: "friendly", "formal", "concise"
        
        Postconditions:
            - Returns non-empty string if LLM is available and call succeeds
            - Returns None if LLM is unavailable or call fails
            - If return value is not None, it contains reworded version of structured_content
            - No side effects on input parameters
        
        Validates: Requirements 8.3, 8.4, 9.7
        """
        if not self.is_available():
            return None
        
        if not structured_content or not structured_content.strip():
            return None
        
        # Build system prompt that prevents medical instruction invention
        system_prompt = (
            f"You are a medical office assistant. Rewrite the following "
            f"appointment preparation instructions in a {tone} tone. "
            f"CRITICAL RULES:\n"
            f"- DO NOT add, remove, or modify any medical instructions, requirements, or warnings\n"
            f"- DO NOT invent new medical advice or preparation steps\n"
            f"- ONLY improve the wording, flow, and readability\n"
            f"- Keep all specific times, items, and requirements exactly as stated\n"
            f"- Preserve all safety warnings and important notices\n"
            f"- Maintain the same level of detail and completeness"
        )
        
        # Try each model in the fallback chain
        for i, model in enumerate(self.models):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": structured_content}
                    ],
                    temperature=0.7,
                    max_tokens=2048
                )
                
                # Extract the rewritten message
                rewritten = response.choices[0].message.content
                
                # Validate that we got a non-empty response
                if rewritten and rewritten.strip():
                    if i > 0:
                        # Log success if using fallback model
                        logger.info(f"Model {model} (fallback #{i}) succeeded")
                    return rewritten.strip()
                    
            except Exception as e:
                # Log warning and try next model
                import logging
                logger = logging.getLogger(__name__)
                
                if i < len(self.models) - 1:
                    logger.warning(f"Model {model} failed: {type(e).__name__}, trying next model")
                else:
                    logger.warning(f"All {len(self.models)} models failed, using template fallback")
        
        # All models failed, return None to trigger template fallback
        return None
    
    def generate_with_prompt(self, system_prompt: str, user_content: str) -> Optional[str]:
        """
        Generate text with custom system prompt.
        
        This method provides a flexible interface for generating text with
        custom system prompts. It's used when more control over the LLM's
        behavior is needed beyond simple rewriting.
        
        Args:
            system_prompt: Custom system prompt to guide LLM behavior
            user_content: User content to process
        
        Returns:
            Generated text if successful, None if LLM unavailable or call fails
        
        Preconditions:
            - system_prompt is a non-empty string
            - user_content is a non-empty string
        
        Postconditions:
            - Returns non-empty string if LLM is available and call succeeds
            - Returns None if LLM is unavailable or call fails
            - No side effects on input parameters
        
        Validates: Requirements 8.3, 8.4, 9.7
        """
        if not self.is_available():
            return None
        
        if not system_prompt or not system_prompt.strip():
            return None
        
        if not user_content or not user_content.strip():
            return None
        
        # Try each model in the fallback chain
        for i, model in enumerate(self.models):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.7,
                    max_tokens=2048
                )
                
                # Extract the generated text
                generated = response.choices[0].message.content
                
                # Validate that we got a non-empty response
                if generated and generated.strip():
                    if i > 0:
                        # Log success if using fallback model
                        logger.info(f"Model {model} (fallback #{i}) succeeded")
                    return generated.strip()
                    
            except Exception as e:
                # Log warning and try next model
                import logging
                logger = logging.getLogger(__name__)
                
                if i < len(self.models) - 1:
                    logger.warning(f"Model {model} failed: {type(e).__name__}, trying next model")
                else:
                    logger.warning(f"All {len(self.models)} models failed")
        
        # All models failed, return None
        return None
