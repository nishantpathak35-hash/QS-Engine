"""
QS Quantification Engine — AI / LLM Subsystem
"""

from core.ai.llm_provider import (
    BaseLLMProvider,
    AITaskType,
    LayerClassificationOutput,
    BlockClassificationOutput,
    AnnotationClassificationOutput,
)
from core.ai.gemini_provider import GeminiLLMProvider
from core.ai.huggingface_provider import HuggingFaceLLMProvider
from core.ai.openai_compatible_provider import OpenAICompatibleLLMProvider
from core.ai.ollama_provider import OllamaLLMProvider
from core.ai.deterministic_fallback import DeterministicFallbackLLMProvider
from core.ai.factory import LLMProviderFactory

__all__ = [
    "BaseLLMProvider",
    "AITaskType",
    "LayerClassificationOutput",
    "BlockClassificationOutput",
    "AnnotationClassificationOutput",
    "GeminiLLMProvider",
    "HuggingFaceLLMProvider",
    "OpenAICompatibleLLMProvider",
    "OllamaLLMProvider",
    "DeterministicFallbackLLMProvider",
    "LLMProviderFactory",
]


