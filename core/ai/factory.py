"""
QS Quantification Engine — LLM Provider Factory
Discovers and supplies the appropriate LLM provider based on environment and availability.
"""

from __future__ import annotations
import os
from typing import Optional

from core.ai.llm_provider import BaseLLMProvider
from core.ai.gemini_provider import GeminiLLMProvider
from core.ai.huggingface_provider import HuggingFaceLLMProvider
from core.ai.openai_compatible_provider import OpenAICompatibleLLMProvider
from core.ai.ollama_provider import OllamaLLMProvider
from core.ai.deterministic_fallback import DeterministicFallbackLLMProvider


from pathlib import Path

def _load_env_file():
    """Lightweight zero-dependency .env loader."""
    for p in (Path(".env"), Path("../.env")):
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass


class LLMProviderFactory:
    """Factory to obtain the active free LLM provider from the 100+ free AI list."""

    _override_provider: Optional[BaseLLMProvider] = None

    @classmethod
    def set_provider(cls, provider: Optional[BaseLLMProvider]) -> None:
        """Sets an explicit provider instance (useful for testing and dependency injection)."""
        cls._override_provider = provider

    @classmethod
    def get_provider(cls) -> BaseLLMProvider:
        """Returns the best available provider."""
        _load_env_file()
        if cls._override_provider is not None:
            return cls._override_provider


        # 1. Check for Google Gemini (Free API Key)
        gemini = GeminiLLMProvider()
        if gemini.is_available:
            return gemini

        # 2. Check for Groq / OpenRouter / Custom OpenAI-compatible free endpoint
        openai_compat = OpenAICompatibleLLMProvider()
        if openai_compat.is_available:
            return openai_compat

        # 3. Check for Hugging Face (Free Serverless Token)
        hf = HuggingFaceLLMProvider()
        if hf.is_available:
            return hf

        # 4. Check for Local Ollama
        ollama = OllamaLLMProvider()
        if ollama.is_available:
            return ollama

        # 5. Fallback to Local Deterministic Reasoning Provider
        return DeterministicFallbackLLMProvider()


