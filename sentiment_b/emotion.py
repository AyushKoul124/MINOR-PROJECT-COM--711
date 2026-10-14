"""Component B — Model 2: Fine-grained Emotion Classification (Ekman 6 + Neutral).

Uses ``SamLowe/roberta-base-go_emotions`` (28 GoEmotions labels) and applies
a deterministic mapping into 7 Ekman buckets:

    joy, anger, sadness, disgust, surprise, fear, neutral

The mapping aggregates the 28 fine-grained labels via max-pooling within
each bucket.  ``dominant_emotion`` is the bucket with the highest aggregated
score, and ``emotion_confidence`` is that score.

Usage (standalone)::

    from sentiment_b.emotion import EmotionClassifier
    clf = EmotionClassifier()
    result = clf.predict("This is absolutely disgusting and outrageous!")
    # => EmotionResult(dominant_emotion='anger', emotion_confidence=0.87, ...)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger("sentiment_b.emotion")

MODEL_ID = "SamLowe/roberta-base-go_emotions"

# ── GoEmotions 28-label → Ekman 6 + Neutral deterministic mapping ────────
# Each GoEmotions label maps to exactly one Ekman bucket.
# We aggregate via max-pool (take the highest probability within each bucket).
GOEMOTIONS_TO_EKMAN: dict[str, str] = {
    # Joy bucket
    "admiration": "joy",
    "amusement": "joy",
    "approval": "joy",
    "caring": "joy",
    "desire": "joy",
    "excitement": "joy",
    "gratitude": "joy",
    "joy": "joy",
    "love": "joy",
    "optimism": "joy",
    "pride": "joy",
    "relief": "joy",
    # Anger bucket
    "anger": "anger",
    "annoyance": "anger",
    "disapproval": "anger",
    # Sadness bucket
    "sadness": "sadness",
    "disappointment": "sadness",
    "embarrassment": "sadness",
    "grief": "sadness",
    "remorse": "sadness",
    # Disgust bucket
    "disgust": "disgust",
    # Surprise bucket
    "surprise": "surprise",
    "curiosity": "surprise",
    "confusion": "surprise",
    "realization": "surprise",
    # Fear bucket
    "fear": "fear",
    "nervousness": "fear",
    # Neutral bucket
    "neutral": "neutral",
}


@dataclass(frozen=True)
class EmotionResult:
    """Immutable result from the Ekman emotion classifier."""

    dominant_emotion: str     # One of: joy, anger, sadness, disgust, surprise, fear, neutral
    emotion_confidence: float # Max aggregated probability of the dominant Ekman bucket (0.0–1.0)
    emotion_joy: float
    emotion_anger: float
    emotion_sadness: float
    emotion_disgust: float
    emotion_surprise: float
    emotion_fear: float
    emotion_neutral: float


class EmotionClassifier:
    """Lazy-loading GoEmotions → Ekman 6 emotion classifier.

    Loads model weights on first call to :meth:`predict` and caches them.
    Callers should call :meth:`unload` between models in the sequential
    pipeline to honour the 4 GB VRAM budget.
    """

    def __init__(self, device: str | None = None) -> None:
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = None
        self._model = None
        self._label_names: list[str] = []  # populated on load

    # ── Lifecycle ─────────────────────────────────────────────────────────
    def _load(self) -> None:
        if self._model is not None:
            return
        logger.info("Loading emotion model: %s → %s", MODEL_ID, self._device)
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_ID, local_files_only=True
        ).to(self._device)
        self._model.eval()
        # Read label ordering from the model config
        self._label_names = [
            self._model.config.id2label[i]
            for i in range(len(self._model.config.id2label))
        ]
        logger.info(
            "Emotion model loaded (%d labels): %s",
            len(self._label_names),
            ", ".join(self._label_names[:5]) + "…",
        )

    def unload(self) -> None:
        """Release model weights and free GPU memory."""
        if self._model is not None:
            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            self._label_names = []
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Emotion model unloaded, GPU cache cleared.")

    # ── Inference ─────────────────────────────────────────────────────────
    def _aggregate_ekman(self, label_probs: dict[str, float]) -> dict[str, float]:
        """Aggregate 28 GoEmotions probabilities into 7 Ekman buckets via max-pool."""
        ekman_scores: dict[str, float] = {
            "joy": 0.0,
            "anger": 0.0,
            "sadness": 0.0,
            "disgust": 0.0,
            "surprise": 0.0,
            "fear": 0.0,
            "neutral": 0.0,
        }

        for label, prob in label_probs.items():
            ekman_bucket = GOEMOTIONS_TO_EKMAN.get(label)
            if ekman_bucket and prob > ekman_scores[ekman_bucket]:
                ekman_scores[ekman_bucket] = prob

        return ekman_scores

    @torch.inference_mode()
    def predict(self, text: str) -> EmotionResult:
        """Classify a single text into Ekman 6 emotion dimensions + neutral.

        Args:
            text: Raw post text.

        Returns:
            EmotionResult with dominant emotion, confidence, and all 7 scores.
        """
        self._load()

        if not text or not text.strip():
            return EmotionResult(
                dominant_emotion="neutral",
                emotion_confidence=1.0,
                emotion_joy=0.0,
                emotion_anger=0.0,
                emotion_sadness=0.0,
                emotion_disgust=0.0,
                emotion_surprise=0.0,
                emotion_fear=0.0,
                emotion_neutral=1.0,
            )

        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        ).to(self._device)

        outputs = self._model(**inputs)
        # GoEmotions is multi-label: apply sigmoid, not softmax
        probs = torch.sigmoid(outputs.logits).squeeze().cpu().tolist()

        # Build label → probability mapping
        label_probs = {
            label: round(prob, 4)
            for label, prob in zip(self._label_names, probs)
        }

        # Aggregate into Ekman 6 + neutral
        ekman = self._aggregate_ekman(label_probs)

        # Determine dominant emotion
        dominant = max(ekman, key=ekman.get)  # type: ignore[arg-type]
        confidence = ekman[dominant]

        return EmotionResult(
            dominant_emotion=dominant,
            emotion_confidence=round(confidence, 4),
            emotion_joy=round(ekman["joy"], 4),
            emotion_anger=round(ekman["anger"], 4),
            emotion_sadness=round(ekman["sadness"], 4),
            emotion_disgust=round(ekman["disgust"], 4),
            emotion_surprise=round(ekman["surprise"], 4),
            emotion_fear=round(ekman["fear"], 4),
            emotion_neutral=round(ekman["neutral"], 4),
        )

    @torch.inference_mode()
    def predict_batch(self, texts: list[str]) -> list[EmotionResult]:
        """Classify a batch of texts into Ekman emotion dimensions.

        Args:
            texts: List of raw post texts.

        Returns:
            List of EmotionResult, one per input text.
        """
        self._load()

        results: list[EmotionResult | None] = [None] * len(texts)
        valid_indices = []
        valid_texts = []

        for i, t in enumerate(texts):
            if not t or not t.strip():
                results[i] = EmotionResult(
                    dominant_emotion="neutral",
                    emotion_confidence=1.0,
                    emotion_joy=0.0,
                    emotion_anger=0.0,
                    emotion_sadness=0.0,
                    emotion_disgust=0.0,
                    emotion_surprise=0.0,
                    emotion_fear=0.0,
                    emotion_neutral=1.0,
                )
            else:
                valid_indices.append(i)
                valid_texts.append(t)

        if valid_texts:
            inputs = self._tokenizer(
                valid_texts,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            ).to(self._device)

            outputs = self._model(**inputs)
            all_probs = torch.sigmoid(outputs.logits).cpu().tolist()

            for idx, probs in zip(valid_indices, all_probs):
                label_probs = {
                    label: round(prob, 4)
                    for label, prob in zip(self._label_names, probs)
                }
                ekman = self._aggregate_ekman(label_probs)
                dominant = max(ekman, key=ekman.get)  # type: ignore[arg-type]

                results[idx] = EmotionResult(
                    dominant_emotion=dominant,
                    emotion_confidence=round(ekman[dominant], 4),
                    emotion_joy=round(ekman["joy"], 4),
                    emotion_anger=round(ekman["anger"], 4),
                    emotion_sadness=round(ekman["sadness"], 4),
                    emotion_disgust=round(ekman["disgust"], 4),
                    emotion_surprise=round(ekman["surprise"], 4),
                    emotion_fear=round(ekman["fear"], 4),
                    emotion_neutral=round(ekman["neutral"], 4),
                )

        return results  # type: ignore[return-value]
