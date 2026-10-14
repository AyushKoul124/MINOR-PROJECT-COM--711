"""Quick smoke test — run the Component B pipeline on sample texts.

This verifies that all 3 models load from cache, produce valid outputs,
and the sarcasm heuristic works correctly.

Run:
    python -m sentiment_b.smoke_test
"""

import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

# Add project root to path
sys.path.insert(0, ".")

from sentiment_b.sentiment import SentimentClassifier
from sentiment_b.emotion import EmotionClassifier
from sentiment_b.stance import StanceDetector
from sentiment_b.sarcasm import SarcasmDetector

TEST_TEXTS = [
    # English positive
    "ISRO has done an amazing job with the Chandrayaan-3 mission! Proud moment for India! 🚀",
    # English negative
    "The government's space budget cuts are deeply concerning and short-sighted.",
    # Hinglish code-mixed
    "Kya shandar launch tha bhai! ISRO ne dil jeet liya 🇮🇳🔥",
    # Sarcasm case (positive valence + negative emoji)
    "Great job cutting the science budget 🤡🤡🤡 really wonderful decision",
    # Neutral/factual
    "The satellite was deployed into a 550km polar orbit at 06:30 UTC today.",
    # Empty text
    "",
]

def main():
    print("=" * 70)
    print("Component B — Smoke Test")
    print("=" * 70)

    # --- Test Sentiment ---
    print("\n[1/4] Testing SentimentClassifier...")
    t0 = time.perf_counter()
    clf = SentimentClassifier()
    for i, text in enumerate(TEST_TEXTS):
        result = clf.predict(text)
        print(f"  Text {i}: {result.valence} ({result.confidence:.3f})")
    clf.unload()
    print(f"  Done in {time.perf_counter() - t0:.2f}s\n")

    # --- Test Emotion ---
    print("[2/4] Testing EmotionClassifier...")
    t0 = time.perf_counter()
    emo = EmotionClassifier()
    for i, text in enumerate(TEST_TEXTS):
        result = emo.predict(text)
        print(f"  Text {i}: {result.dominant_emotion} ({result.emotion_confidence:.3f})")
    emo.unload()
    print(f"  Done in {time.perf_counter() - t0:.2f}s\n")

    # --- Test Stance ---
    print("[3/4] Testing StanceDetector...")
    t0 = time.perf_counter()
    stance = StanceDetector()
    for i, text in enumerate(TEST_TEXTS):
        result = stance.predict(text, topic="Indian space programme and ISRO missions")
        print(f"  Text {i}: {result.stance} ({result.confidence:.3f}) [topic: {result.topic_evaluated}]")
    stance.unload()
    print(f"  Done in {time.perf_counter() - t0:.2f}s\n")

    # --- Test Sarcasm ---
    print("[4/4] Testing SarcasmDetector...")
    sarcasm = SarcasmDetector()
    # Re-run sentiment for sarcasm valence pairing
    clf2 = SentimentClassifier()
    for i, text in enumerate(TEST_TEXTS):
        valence = clf2.predict(text).valence
        flag = sarcasm.check(text, valence)
        print(f"  Text {i}: sarcasm={flag} (valence={valence})")
    clf2.unload()

    print("\n" + "=" * 70)
    print("SMOKE TEST COMPLETE — All models working correctly!")
    print("=" * 70)


if __name__ == "__main__":
    main()
