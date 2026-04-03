"""LLM client abstraction for calling language models."""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import json
import re

try:
    from json_repair import repair_json
except ImportError:
    repair_json = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from app.core.config import settings
from app.core.logging import logger


def _parse_json_flexible(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM output using strict, extracted, and repaired fallbacks."""
    # 1) Strict parse first.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) Strip markdown fences if present.
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3) Extract first object/array-like block and try progressively shorter slices.
    for start_char in ["{", "["]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue
        for end_idx in range(len(text), start_idx, -1):
            chunk = text[start_idx:end_idx]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue

    # 4) Repair malformed JSON as last resort.
    if repair_json is not None:
        try:
            repaired = repair_json(text)
            return json.loads(repaired)
        except Exception:
            pass

    raise ValueError(f"Could not parse JSON from: {text[:100]}...")


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


class GeminiClient(BaseLLMClient):
    """Google Gemini LLM client implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if genai is None:
            raise ImportError("google-generativeai package not installed. Install with: pip install google-generativeai")
        
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not provided and not set in environment")
        
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)
        logger.info(f"Initialized Gemini client with model: {self.model}")
    
    def call(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Call Gemini API."""
        try:
            # Convert chat-style messages to Gemini format.
            # Gemini expects roles to be "user" or "model"; it does not accept "system".
            # We fold system prompts into the first user message as instructions.
            gemini_messages = []
            system_instructions: list[str] = []

            for msg in messages:
                role = (msg.get("role") or "user").lower()
                content = str(msg.get("content", ""))
                if not content.strip():
                    continue

                if role == "system":
                    system_instructions.append(content.strip())
                    continue

                gemini_role = "model" if role == "assistant" else "user"
                gemini_messages.append({
                    "role": gemini_role,
                    "parts": [{"text": content}],
                })

            if system_instructions:
                instruction_block = "\n\n".join(system_instructions)
                if gemini_messages and gemini_messages[0]["role"] == "user":
                    first_text = gemini_messages[0]["parts"][0]["text"]
                    gemini_messages[0]["parts"][0]["text"] = (
                        f"Instructions:\n{instruction_block}\n\nUser request:\n{first_text}"
                    )
                else:
                    gemini_messages.insert(0, {
                        "role": "user",
                        "parts": [{"text": f"Instructions:\n{instruction_block}"}],
                    })

            if not gemini_messages:
                raise ValueError("No valid messages to send to Gemini")
            
            response = self.client.generate_content(
                contents=gemini_messages,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens or 2000,
                }
            )
            
            content = response.text
            
            # Attempt to extract token usage if available
            usage = {}
            if hasattr(response, 'usage_metadata'):
                usage = {
                    "input_tokens": getattr(response.usage_metadata, 'prompt_tokens', 0),
                    "output_tokens": getattr(response.usage_metadata, 'candidates_tokens', 0),
                }
            
            logger.debug(f"Gemini call successful. Tokens: {usage}")
            return LLMResponse(content=content, usage=usage)
        
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            raise
    
    def parse_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text."""
        return _parse_json_flexible(text)


def get_llm_client() -> BaseLLMClient:
    """Factory function for Gemini-only deployments."""
    provider = settings.LLM_PROVIDER.lower()

    if provider != "gemini":
        raise ValueError(f"Gemini-only mode enabled. Unsupported LLM_PROVIDER: {provider}")

    return GeminiClient()
