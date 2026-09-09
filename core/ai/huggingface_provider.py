"""
QS Quantification Engine — Free Hugging Face LLM Provider
Uses Hugging Face Free Serverless Inference API (Qwen 2.5, Llama 3.2, Mistral).
Enables ₹0 cloud inference via Hugging Face Free Community tier.
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


class HuggingFaceLLMProvider(BaseLLMProvider):
    """
    Client for Hugging Face Free Serverless Inference API.
    Supports models such as 'Qwen/Qwen2.5-7B-Instruct', 'meta-llama/Llama-3.2-3B-Instruct',
    and 'mistralai/Mistral-7B-Instruct-v0.3' using a free user token (HF_TOKEN).
    """

    DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
    ROUTER_URL = "https://api-inference.huggingface.co/models"

    def __init__(
        self,
        token: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 15.0
    ):
        self.token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
        self.model_name = model_name or os.environ.get("HF_MODEL", self.DEFAULT_MODEL)
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return f"huggingface-free ({self.model_name})"

    @property
    def is_available(self) -> bool:
        return bool(self.token and len(self.token.strip()) > 5)

    def _call_hf(self, prompt: str) -> dict:
        if not self.is_available:
            raise RuntimeError("Hugging Face token not configured. Set HF_TOKEN environment variable.")

        url = f"{self.ROUTER_URL}/{self.model_name}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.1,
                "return_full_text": False
            }
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Extract generated response text
        raw_output = ""
        if isinstance(data, list) and len(data) > 0:
            raw_output = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            raw_output = data.get("generated_text", "") or str(data)

        # Parse JSON block from response
        match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(raw_output)

    def classify_layer(self, layer_name: str, sample_entities: Optional[list[str]] = None) -> LayerClassificationOutput:
        prompt = (
            f"You are a CAD drawing specialist. Classify this layer into one of: "
            f"['wall', 'door', 'window', 'floor_finish', 'ceiling_finish', 'furniture', 'electrical', 'plumbing', 'annotation', 'dimension', 'ignored', 'unknown'].\n"
            f"Layer: \"{layer_name}\"\n"
            f"Return JSON strictly conforming to: {{\"layer_name\": \"{layer_name}\", \"category\": \"<category>\", \"confidence\": 0.9, \"reason\": \"<brief>\"}}"
        )
        try:
            res_dict = self._call_hf(prompt)
            return LayerClassificationOutput(**res_dict)
        except Exception as e:
            return LayerClassificationOutput(layer_name=layer_name, category="unknown", confidence=0.0, reason=str(e))

    def classify_block(self, block_name: str, layer: str, attributes: Optional[dict[str, Any]] = None) -> BlockClassificationOutput:
        prompt = (
            f"Classify CAD block: \"{block_name}\" on layer \"{layer}\" into: "
            f"['door', 'window', 'furniture', 'fixture', 'equipment', 'column', 'unknown'].\n"
            f"Return JSON: {{\"block_name\": \"{block_name}\", \"category\": \"<category>\", \"is_door\": <bool>, \"confidence\": 0.9, \"reason\": \"<brief>\"}}"
        )
        try:
            res_dict = self._call_hf(prompt)
            return BlockClassificationOutput(**res_dict)
        except Exception as e:
            return BlockClassificationOutput(block_name=block_name, category="unknown", is_door=False, confidence=0.0, reason=str(e))

    def classify_annotation(self, text: str) -> AnnotationClassificationOutput:
        prompt = (
            f"Classify drawing note: \"{text}\" into: ['room_name', 'finish_code', 'dimension', 'note', 'unknown'].\n"
            f"Return JSON: {{\"raw_text\": \"{text}\", \"semantic_type\": \"<type>\", \"confidence\": 0.9}}"
        )
        try:
            res_dict = self._call_hf(prompt)
            return AnnotationClassificationOutput(**res_dict)
        except Exception as e:
            return AnnotationClassificationOutput(raw_text=text, semantic_type="unknown", confidence=0.0)
