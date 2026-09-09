"""
QS Quantification Engine — Free Local Ollama LLM Provider
Enables 100% offline, ₹0 compute cost LLM reasoning using Ollama (Llama 3, Qwen 2.5, Mistral).
Enforces Blueprint Section 107 (Local AI Download Strategy) & Section 108 (AI Cost Control).
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


class OllamaLLMProvider(BaseLLMProvider):
    """
    Client for local Ollama running on localhost:11434.
    Runs completely local with zero API fees or data transmission.
    """

    DEFAULT_HOST = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "llama3.2"

    def __init__(
        self,
        host: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 10.0
    ):
        self.host = (host or os.environ.get("OLLAMA_HOST") or self.DEFAULT_HOST).rstrip("/")
        self.model_name = model_name or os.environ.get("OLLAMA_MODEL", self.DEFAULT_MODEL)
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return f"ollama-local ({self.model_name})"

    @property
    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=1.5) as client:
                resp = client.get(f"{self.host}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def _call_ollama(self, prompt: str) -> dict:
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            res_json = resp.json()
            return json.loads(res_json.get("response", "{}"))

    def classify_layer(self, layer_name: str, sample_entities: Optional[list[str]] = None) -> LayerClassificationOutput:
        prompt = (
            f"Classify this CAD drawing layer: \"{layer_name}\" into one category from: "
            f"['wall', 'door', 'window', 'floor_finish', 'ceiling_finish', 'furniture', 'electrical', 'plumbing', 'annotation', 'dimension', 'ignored', 'unknown'].\n"
            f"Respond with JSON: {{\"layer_name\": \"{layer_name}\", \"category\": \"<category>\", \"confidence\": 0.9, \"reason\": \"<why>\"}}"
        )
        try:
            data = self._call_ollama(prompt)
            return LayerClassificationOutput(**data)
        except Exception as e:
            return LayerClassificationOutput(layer_name=layer_name, category="unknown", confidence=0.0, reason=str(e))

    def classify_block(self, block_name: str, layer: str, attributes: Optional[dict[str, Any]] = None) -> BlockClassificationOutput:
        prompt = (
            f"Classify CAD block: \"{block_name}\" on layer \"{layer}\" into: "
            f"['door', 'window', 'furniture', 'fixture', 'equipment', 'column', 'unknown'].\n"
            f"Respond with JSON: {{\"block_name\": \"{block_name}\", \"category\": \"<category>\", \"is_door\": <bool>, \"confidence\": 0.9, \"reason\": \"<why>\"}}"
        )
        try:
            data = self._call_ollama(prompt)
            return BlockClassificationOutput(**data)
        except Exception as e:
            return BlockClassificationOutput(block_name=block_name, category="unknown", is_door=False, confidence=0.0, reason=str(e))

    def classify_annotation(self, text: str) -> AnnotationClassificationOutput:
        prompt = (
            f"Classify drawing text: \"{text}\" into: ['room_name', 'finish_code', 'dimension', 'note', 'unknown'].\n"
            f"Respond with JSON: {{\"raw_text\": \"{text}\", \"semantic_type\": \"<type>\", \"confidence\": 0.9}}"
        )
        try:
            data = self._call_ollama(prompt)
            return AnnotationClassificationOutput(**data)
        except Exception as e:
            return AnnotationClassificationOutput(raw_text=text, semantic_type="unknown", confidence=0.0)
