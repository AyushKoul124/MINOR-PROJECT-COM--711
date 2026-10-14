"""Add extended fine-grained emotions (anxiety, excitement, extended JSONB) to sentiment_results_b.

Revision ID: 0002_add_extended_emotions
Revises: 0001_initial
Create Date: 2026-10-14 22:18:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_extended_emotions"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sentiment_results_b",
        sa.Column("emotion_anxiety", sa.Float(), server_default=sa.text("0.0"), nullable=True),
    )
    op.add_column(
        "sentiment_results_b",
        sa.Column("emotion_excitement", sa.Float(), server_default=sa.text("0.0"), nullable=True),
    )
    op.add_column(
        "sentiment_results_b",
        sa.Column("emotion_extended", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sentiment_results_b", "emotion_extended")
    op.drop_column("sentiment_results_b", "emotion_excitement")
    op.drop_column("sentiment_results_b", "emotion_anxiety")
