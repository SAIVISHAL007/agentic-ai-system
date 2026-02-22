"""LLM client abstraction for calling language models."""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import json

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import openai
except ImportError:
    openai = None

from app.core.config import settings
from app.core.logging import logger


class LLMResponse:
    """Structured LLM response."""
    
    def __init__(self, content: str, usage: Optional[Dict[str, int]] = None):
        self.content = content
        self.usage = usage or {}
    
    def __str__(self) -> str:
        return self.content


class BaseLLMClient(ABC):
    """Abstract base for LLM clients."""
    
    @abstractmethod
    def call(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Call the LLM with a list of messages."""
        pass
    
    @abstractmethod
    def parse_json(self, text: str) -> Dict[str, Any]:
        """Attempt to parse JSON from LLM response."""
        pass


class GroqClient(BaseLLMClient):
    """Groq LLM client implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if Groq is None:
            raise ImportError("groq package not installed. Install with: pip install groq")
        
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not provided and not set in environment")
        
        self.client = Groq(api_key=self.api_key)
        logger.info(f"Initialized Groq client with model: {self.model}")
    
    def call(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Call Groq API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 2000,
            )
            
            content = response.choices[0].message.content
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
            
            logger.debug(f"Groq call successful. Tokens: {usage}")
            return LLMResponse(content=content, usage=usage)
        
        except Exception as e:
            logger.error(f"Groq API call failed: {str(e)}")
            raise
    
    def parse_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text."""
        try:
            # Try direct JSON parsing first
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            for start_char in ['{', '[']:
                start_idx = text.find(start_char)
                if start_idx != -1:
                    for end_idx in range(len(text), start_idx, -1):
                        try:
                            return json.loads(text[start_idx:end_idx])
                        except json.JSONDecodeError:
                            continue
            
            raise ValueError(f"Could not parse JSON from: {text[:100]}...")


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible LLM client implementation."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        if openai is None:
            raise ImportError("openai package not installed. Install with: pip install openai")
        
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.base_url = base_url or settings.OPENAI_BASE_URL
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not provided and not set in environment")
        
        # Initialize OpenAI client (supports base_url for compatible APIs)
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        logger.info(f"Initialized OpenAI client with model: {self.model}")
    
    def call(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Call OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 2000,
            )
            
            content = response.choices[0].message.content
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
            
            logger.debug(f"OpenAI call successful. Tokens: {usage}")
            return LLMResponse(content=content, usage=usage)
        
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise
    
    def parse_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            for start_char in ['{', '[']:
                start_idx = text.find(start_char)
                if start_idx != -1:
                    for end_idx in range(len(text), start_idx, -1):
                        try:
                            return json.loads(text[start_idx:end_idx])
                        except json.JSONDecodeError:
                            continue
            
            raise ValueError(f"Could not parse JSON from: {text[:100]}...")


def get_llm_client() -> BaseLLMClient:
    """Factory function to get LLM client based on configuration."""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "groq":
        return GroqClient()
    elif provider == "openai":
        return OpenAIClient()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
