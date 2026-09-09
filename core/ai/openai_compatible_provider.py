"""
QS Quantification Engine — Universal Free OpenAI-Compatible Provider
Enables seamless integration with any free AI API provider from the collective list:
- Groq (https://groq.com)
- OpenRouter (https://openrouter.ai)
- Cerebras (https://cerebras.ai)
- Mistral AI (https://mistral.ai)
- SambaNova (https://sambanova.ai)
- Together AI (https://together.ai)
Enforces ₹0 cost API operation with standard OpenAI-compatible endpoints.
"""

from __future__ import annotations
import os
import json
import re
from typing import Any, Optional
import httpx

from core.ai.llm_provider import (
    BaseLLMProvider,
    LayerClassificationOutput,
    BlockClassificationOutput,
    AnnotationClassificationOutput,
)


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    """
    Universal client for any OpenAI-compatible free API provider (Groq, OpenRouter, SambaNova, etc.).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider_label: str = "openai-compatible",
        timeout_seconds: float = 15.0
    ):
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or os.environ.get("AI_API_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("GROQ_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.model_name = model_name or os.environ.get("AI_MODEL") or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        self.provider_label = provider_label
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return f"{self.provider_label} ({self.model_name})"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def _call_completion(self, system_prompt: str, user_prompt: str) -> dict:
        if not self.is_available:
            raise RuntimeError(f"{self.provider_label} API key not configured.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"} if "groq" in self.base_url.lower() or "openai" in self.base_url.lower() else None
        }

        # Filter out None values
        payload = {k: v for k, v in payload.items() if v is not None}

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(content)

    def classify_layer(self, layer_name: str, sample_entities: Optional[list[str]] = None) -> LayerClassificationOutput:
        sys_p = "You are a CAD drawing specialist. Output valid JSON only."
        user_p = (
            f"Classify CAD layer: \"{layer_name}\" into one category from: "
            f"['wall', 'door', 'window', 'floor_finish', 'ceiling_finish', 'furniture', 'electrical', 'plumbing', 'annotation', 'dimension', 'ignored', 'unknown'].\n"
            f"Return JSON: {{\"layer_name\": \"{layer_name}\", \"category\": \"<category>\", \"confidence\": 0.9, \"reason\": \"<brief>\"}}"
        )
        try:
            res_dict = self._call_completion(sys_p, user_p)
            return LayerClassificationOutput(**res_dict)
        except Exception as e:
            return LayerClassificationOutput(layer_name=layer_name, category="unknown", confidence=0.0, reason=str(e))

    def classify_block(self, block_name: str, layer: str, attributes: Optional[dict[str, Any]] = None) -> BlockClassificationOutput:
        sys_p = "You are an architectural CAD specialist. Output valid JSON only."
        user_p = (
            f"Classify CAD block: \"{block_name}\" on layer \"{layer}\" into: "
            f"['door', 'window', 'furniture', 'fixture', 'equipment', 'column', 'unknown'].\n"
            f"Return JSON: {{\"block_name\": \"{block_name}\", \"category\": \"<category>\", \"is_door\": <bool>, \"confidence\": 0.9, \"reason\": \"<brief>\"}}"
        )
        try:
            res_dict = self._call_completion(sys_p, user_p)
            return BlockClassificationOutput(**res_dict)
        except Exception as e:
            return BlockClassificationOutput(block_name=block_name, category="unknown", is_door=False, confidence=0.0, reason=str(e))

    def classify_annotation(self, text: str) -> AnnotationClassificationOutput:
        sys_p = "You are an architectural drawing specialist. Output valid JSON only."
        user_p = (
            f"Classify drawing note: \"{text}\" into: ['room_name', 'finish_code', 'dimension', 'note', 'unknown'].\n"
            f"Return JSON: {{\"raw_text\": \"{text}\", \"semantic_type\": \"<type>\", \"confidence\": 0.9}}"
        )
        try:
            res_dict = self._call_completion(sys_p, user_p)
            return AnnotationClassificationOutput(**res_dict)
        except Exception as e:
            return AnnotationClassificationOutput(raw_text=text, semantic_type="unknown", confidence=0.0)
