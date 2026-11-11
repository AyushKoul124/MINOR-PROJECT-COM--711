"""Store the emoji-reaction heuristic on sentiment_results_b.

Revision ID: 0003_add_reaction_scores
Revises: 0002_add_extended_emotions
Create Date: 2026-11-10 20:50:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_add_reaction_scores"
down_revision: Union[str, None] = "0002_add_extended_emotions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sentiment_results_b", sa.Column("reaction_valence", sa.String(length=16), nullable=True))
    op.add_column("sentiment_results_b", sa.Column("reaction_score", sa.Float(), nullable=True))
    op.add_column(
        "sentiment_results_b",
        sa.Column("reaction_total", sa.Integer(), server_default=sa.text("0"), nullable=True),
    )
    op.add_column(
        "sentiment_results_b",
        sa.Column("reaction_positive", sa.Integer(), server_default=sa.text("0"), nullable=True),
    )
    op.add_column(
        "sentiment_results_b",
        sa.Column("reaction_negative", sa.Integer(), server_default=sa.text("0"), nullable=True),
    )
    op.add_column(
        "sentiment_results_b",
        sa.Column("reaction_other", sa.Integer(), server_default=sa.text("0"), nullable=True),
    )
    op.add_column(
        "sentiment_results_b",
        sa.Column("reaction_top", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sentiment_results_b", "reaction_top")
    op.drop_column("sentiment_results_b", "reaction_other")
    op.drop_column("sentiment_results_b", "reaction_negative")
    op.drop_column("sentiment_results_b", "reaction_positive")
    op.drop_column("sentiment_results_b", "reaction_total")
    op.drop_column("sentiment_results_b", "reaction_score")
    op.drop_column("sentiment_results_b", "reaction_valence")
