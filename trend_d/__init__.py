"""Component D: Trend & Topic Discovery Agent.

Neural topic extraction via BERTopic, outlier reduction via c-TF-IDF, and
temporal velocity (posts/hr) and acceleration calculations strictly anchored
to platform ``raw_posts.posted_at`` UTC timestamps.
"""

from trend_d.agent import TrendAgent, TrendRunResult
from trend_d.summary import generate_trend_summary
from trend_d.topic_model import (
    TopicDefinition,
    TopicModeler,
    TopicModelingResult,
)
from trend_d.velocity import TopicVelocityMetrics, VelocityEngine

__all__ = [
    "TrendAgent",
    "TrendRunResult",
    "TopicModeler",
    "TopicDefinition",
    "TopicModelingResult",
    "VelocityEngine",
    "TopicVelocityMetrics",
    "generate_trend_summary",
]
