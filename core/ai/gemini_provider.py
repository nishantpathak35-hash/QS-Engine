"""
QS Quantification Engine — Free Google Gemini LLM Provider
Uses Google's free-tier Gemini Flash models for ambiguous CAD entity classification.
100% Zero-cost API tier on Google AI Studio.
"""

from __future__ import annotations
import os
import json
from typing import Any, Optional
import httpx

from core.ai.llm_provider import (
    BaseLLMProvider,
    LayerClassificationOutput,
    BlockClassificationOutput,
    AnnotationClassificationOutput,
)


class GeminiLLMProvider(BaseLLMProvider):
    """
    Direct client for Google Gemini API Free Tier.
    Uses 'gemini-1.5-flash' or 'gemini-2.5-flash' with structured JSON responses.
    """

    DEFAULT_MODEL = "gemini-1.5-flash"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 15.0
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return f"google-gemini-free ({self.model_name})"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def _call_gemini_json(self, prompt: str, schema_class: type) -> dict:
        """Invokes Gemini API with JSON response enforcement."""
        if not self.is_available:
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY environment variable.")

        url = f"{self.BASE_URL}/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            }
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw_text)

    def classify_layer(self, layer_name: str, sample_entities: Optional[list[str]] = None) -> LayerClassificationOutput:
        prompt = (
            f"You are a CAD architecture expert. Classify the following non-standard CAD drawing layer into one of these exact categories: "
            f"['wall', 'door', 'window', 'floor_finish', 'ceiling_finish', 'furniture', 'electrical', 'plumbing', 'annotation', 'dimension', 'ignored', 'unknown'].\n"
            f"Layer Name: \"{layer_name}\"\n"
            f"Sample entities on layer: {sample_entities or []}\n"
            f"Return JSON strictly conforming to: {{\"layer_name\": \"{layer_name}\", \"category\": \"<category>\", \"confidence\": <float 0-1>, \"reason\": \"<brief explanation>\"}}"
        )
        try:
            res_dict = self._call_gemini_json(prompt, LayerClassificationOutput)
            return LayerClassificationOutput(**res_dict)
        except Exception as e:
            return LayerClassificationOutput(
                layer_name=layer_name,
                category="unknown",
                confidence=0.0,
                reason=f"Gemini error: {str(e)}"
            )

    def classify_block(self, block_name: str, layer: str, attributes: Optional[dict[str, Any]] = None) -> BlockClassificationOutput:
        prompt = (
            f"You are a CAD drawing specialist. Classify this architectural block into one of: "
            f"['door', 'window', 'furniture', 'fixture', 'equipment', 'column', 'unknown'].\n"
            f"Block Name: \"{block_name}\"\n"
            f"Host Layer: \"{layer}\"\n"
            f"Attributes: {attributes or {}}\n"
            f"Return JSON strictly conforming to: {{\"block_name\": \"{block_name}\", \"category\": \"<category>\", \"is_door\": <bool>, \"confidence\": <float 0-1>, \"reason\": \"<brief explanation>\"}}"
        )
        try:
            res_dict = self._call_gemini_json(prompt, BlockClassificationOutput)
            return BlockClassificationOutput(**res_dict)
        except Exception as e:
            return BlockClassificationOutput(
                block_name=block_name,
                category="unknown",
                is_door=False,
                confidence=0.0,
                reason=f"Gemini error: {str(e)}"
            )

    def classify_annotation(self, text: str) -> AnnotationClassificationOutput:
        prompt = (
            f"Classify this drawing text note into: ['room_name', 'finish_code', 'dimension', 'note', 'unknown'].\n"
            f"Text: \"{text}\"\n"
            f"Return JSON: {{\"raw_text\": \"{text}\", \"semantic_type\": \"<type>\", \"normalized_value\": \"<val or null>\", \"confidence\": <float 0-1>}}"
        )
        try:
            res_dict = self._call_gemini_json(prompt, AnnotationClassificationOutput)
            return AnnotationClassificationOutput(**res_dict)
        except Exception as e:
            return AnnotationClassificationOutput(
                raw_text=text,
                semantic_type="unknown",
                confidence=0.0
            )
