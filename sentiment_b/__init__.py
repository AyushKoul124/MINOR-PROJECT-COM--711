"""Component B: Sentiment, Emotion & Stance Agent.

Sequential 3-model NLP pipeline:
    1. SentimentClassifier  — Multilingual 3-class valence (XLM-RoBERTa)
    2. EmotionClassifier    — Ekman 6 + neutral emotions (GoEmotions)
    3. StanceDetector       — Zero-shot policy stance (DistilBART MNLI)
    4. SarcasmDetector      — Rule-based valence-emoji incongruity heuristic

Orchestrated by SentimentPipeline, which enforces the 4 GB VRAM sequential
execution invariant (load → infer → unload → empty_cache between models).
"""

from sentiment_b.emotion import EmotionClassifier, EmotionResult
from sentiment_b.pipeline import SentimentPipeline
from sentiment_b.sarcasm import SarcasmDetector
from sentiment_b.sentiment import SentimentClassifier, SentimentResult
from sentiment_b.stance import StanceDetector, StanceResult

__all__ = [
    "SentimentPipeline",
    "SentimentClassifier",
    "SentimentResult",
    "EmotionClassifier",
    "EmotionResult",
    "StanceDetector",
    "StanceResult",
    "SarcasmDetector",
]
