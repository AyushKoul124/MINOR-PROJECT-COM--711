"""RAG Layer — Dual-Tier LLM Client and Extractive Synthesizer.

Provides grounded answer synthesis over retrieved intelligence documents:
    - Tier 1: Local Ollama (llama3.2:3b on CPU via OLLAMA_NUM_GPU=0) — primary offline viva engine.
    - Tier 2: Groq Cloud API (llama-3.3-70b-versatile) — optional high-accuracy depth when online.
    - Fallback: Deterministic Extractive Synthesizer — guaranteed zero-error fallback.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("rag.llm")

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    answer_text: str
    provider: str
    model_name: str
    cited_doc_ids: list[str]
    confidence: float
    is_grounded: bool


class BaseLLMClient:
    """Base interface for RAG generation providers."""

    def generate_grounded_answer(
        self,
        query: str,
        context_docs: list[dict[str, Any]],
    ) -> LLMResponse:
        raise NotImplementedError


class OllamaClient(BaseLLMClient):
    """Local air-gapped inference client connecting to Ollama daemon."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.timeout = timeout_seconds

    def is_available(self) -> bool:
        """Ping Ollama daemon to check connectivity."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate_grounded_answer(
        self,
        query: str,
        context_docs: list[dict[str, Any]],
    ) -> LLMResponse:
        """Prompt Ollama to answer using only retrieved context."""
        context_str = "\n\n".join(
            f"--- Document [{d['doc_id']}] (Component {d['source_component']}) ---\n{d['content_text']}"
            for d in context_docs
        )
        prompt = (
            "You are an academic intelligence research assistant. Answer the user's question "
            "strictly and factually based on the provided intelligence documents below. "
            "If the context does not contain sufficient facts to answer, explicitly state that. "
            "Always cite document references as [Doc: <doc_id>].\n\n"
            f"Context Documents:\n{context_str}\n\n"
            f"Analyst Question: {query}\n\n"
            "Grounded Answer:"
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 300},
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                ans = res_json.get("response", "").strip()
                cited_ids = [d["doc_id"] for d in context_docs if d["doc_id"] in ans]
                if not cited_ids and context_docs:
                    cited_ids = [context_docs[0]["doc_id"]]

                return LLMResponse(
                    answer_text=ans,
                    provider="ollama_local",
                    model_name=self.model,
                    cited_doc_ids=cited_ids,
                    confidence=0.88,
                    is_grounded=True,
                )
        except Exception as exc:
            logger.warning("Ollama generation failed (%s), falling back...", exc)
            raise


class GroqClient(BaseLLMClient):
    """Optional cloud provider via Groq OpenAI-compatible completions API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 10)

    def generate_grounded_answer(
        self,
        query: str,
        context_docs: list[dict[str, Any]],
    ) -> LLMResponse:
        context_str = "\n\n".join(
            f"--- Document [{d['doc_id']}] (Component {d['source_component']}) ---\n{d['content_text']}"
            for d in context_docs
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a factual intelligence analysis assistant. Answer using ONLY "
                    "the provided context documents. Cite sources as [Doc: <doc_id>]."
                ),
            },
            {
                "role": "user",
                "content": f"Context Documents:\n{context_str}\n\nQuestion: {query}",
            },
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 400,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10.0) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            ans = res_json["choices"][0]["message"]["content"].strip()
            cited_ids = [d["doc_id"] for d in context_docs if d["doc_id"] in ans]
            if not cited_ids and context_docs:
                cited_ids = [context_docs[0]["doc_id"]]

            return LLMResponse(
                answer_text=ans,
                provider="groq_cloud",
                model_name=self.model,
                cited_doc_ids=cited_ids,
                confidence=0.92,
                is_grounded=True,
            )


class ExtractiveSynthesizerClient(BaseLLMClient):
    """Deterministic, zero-internet extractive synthesizer.

    Synthesizes concise, grounded answers directly from the highest-ranked
    evidence snippets without requiring any running LLM server.
    """

    def generate_grounded_answer(
        self,
        query: str,
        context_docs: list[dict[str, Any]],
    ) -> LLMResponse:
        if not context_docs:
            return LLMResponse(
                answer_text="No grounded intelligence records were found for this query.",
                provider="extractive_synthesis",
                model_name="deterministic_extractive",
                cited_doc_ids=[],
                confidence=0.0,
                is_grounded=False,
            )

        top_doc = context_docs[0]
        cited_ids = [d["doc_id"] for d in context_docs[:3]]

        snippets = []
        for i, doc in enumerate(context_docs[:3], 1):
            text_clean = doc["content_text"].strip()
            snippets.append(f"({i}) [Doc {doc['doc_id'][:8]}]: {text_clean}")

        body = " ".join(snippets)
        answer = (
            f"Based on grounded intelligence records for inquiry '{query}', the system retrieved "
            f"{len(context_docs)} relevant analytical entries (top similarity: {top_doc.get('similarity_score', 1.0):.2f}). "
            f"Key findings: {body}"
        )

        return LLMResponse(
            answer_text=answer,
            provider="extractive_synthesis",
            model_name="deterministic_extractive",
            cited_doc_ids=cited_ids,
            confidence=round(float(top_doc.get("similarity_score", 0.85)), 2),
            is_grounded=True,
        )


class RouterLLMClient(BaseLLMClient):
    """Dual-tier router: tries Ollama -> Groq -> Extractive Synthesizer."""

    def __init__(self) -> None:
        self.ollama = OllamaClient()
        self.groq = GroqClient()
        self.extractive = ExtractiveSynthesizerClient()

    def generate_grounded_answer(
        self,
        query: str,
        context_docs: list[dict[str, Any]],
    ) -> LLMResponse:
        # Tier 1: Local Ollama (Primary Offline Viva Engine)
        if self.ollama.is_available():
            try:
                logger.info("Routing query to local Ollama (%s)...", self.ollama.model)
                return self.ollama.generate_grounded_answer(query, context_docs)
            except Exception as exc:
                logger.warning("Ollama execution failed (%s), attempting fallback...", exc)

        # Tier 2: Groq Cloud API (Optional online depth)
        if self.groq.is_available():
            try:
                logger.info("Routing query to Groq Cloud (%s)...", self.groq.model)
                return self.groq.generate_grounded_answer(query, context_docs)
            except Exception as exc:
                logger.warning("Groq execution failed (%s), attempting fallback...", exc)

        # Tier 3: Deterministic Extractive Synthesizer (Deterministic viva safety net)
        logger.info("Routing query to deterministic Extractive Synthesizer...")
        return self.extractive.generate_grounded_answer(query, context_docs)
