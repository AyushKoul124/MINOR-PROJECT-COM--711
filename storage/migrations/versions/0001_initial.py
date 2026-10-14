"""Initial schema migration: pgvector extension and all core SOCMINT tables.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. HARD INVARIANT: Enable pgvector extension before any table uses vector(384)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Monitored Channels table
    op.create_table(
        "monitored_channels",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=512), nullable=False),
        sa.Column("topic_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_polled_message_id", sa.BigInteger(), server_default=sa.text("0"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier", name="uq_monitored_channels_identifier"),
    )
    op.create_index("idx_monitored_channels_identifier", "monitored_channels", ["identifier"])

    # 3. Ingestion Runs table
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform", sa.String(length=32), server_default=sa.text("'telegram'"), nullable=False),
        sa.Column("channel_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("posts_collected", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'running'"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Raw Posts table
    op.create_table(
        "raw_posts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(length=32), server_default=sa.text("'telegram'"), nullable=False),
        sa.Column("platform_post_id", sa.String(length=255), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("author_id", sa.String(length=255), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_language", sa.String(length=16), nullable=True),
        sa.Column("media_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reply_to_id", sa.String(length=255), nullable=True),
        sa.Column("forward_from_id", sa.String(length=255), nullable=True),
        sa.Column("view_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("reaction_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("processing_status", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "platform_post_id", name="uq_raw_posts_platform_post_id"),
    )
    op.create_index("idx_raw_posts_posted_at", "raw_posts", ["posted_at"])
    op.create_index("idx_raw_posts_channel_id", "raw_posts", ["channel_id"])
    op.execute("CREATE INDEX idx_raw_posts_pending ON raw_posts (id) WHERE processing_status = 'pending';")

    # 5. Raw Authors table
    op.create_table(
        "raw_authors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(length=32), server_default=sa.text("'telegram'"), nullable=False),
        sa.Column("platform_author_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=512), nullable=True),
        sa.Column("bio_text", sa.Text(), nullable=True),
        sa.Column("follower_count", sa.Integer(), nullable=True),
        sa.Column("account_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_raw_authors_platform_author_id", "raw_authors", ["platform_author_id"])

    # 6. Component B: Sentiment Results table
    op.create_table(
        "sentiment_results_b",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("raw_post_id", sa.BigInteger(), nullable=False),
        sa.Column("content_language", sa.String(length=16), server_default=sa.text("'en'"), nullable=False),
        sa.Column("dominant_emotion", sa.String(length=64), nullable=True),
        sa.Column("emotion_confidence", sa.Float(), nullable=True),
        sa.Column("emotion_joy", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("emotion_anger", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("emotion_sadness", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("emotion_disgust", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("emotion_surprise", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("emotion_neutral", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("emotion_fear", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("stance", sa.String(length=32), server_default=sa.text("'neutral'"), nullable=True),
        sa.Column("stance_confidence", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("sarcasm_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("valence", sa.String(length=16), server_default=sa.text("'neutral'"), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["raw_post_id"], ["raw_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_post_id", name="uq_sentiment_results_b_post_id"),
    )
    op.create_index("idx_sentiment_b_post_id", "sentiment_results_b", ["raw_post_id"])
    op.create_index("idx_sentiment_b_analyzed_at", "sentiment_results_b", ["analyzed_at"])

    # 7. Component C: Demographic Aggregates table
    op.create_table(
        "demographic_aggregates_c",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cluster_label", sa.String(length=255), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_count", sa.Integer(), nullable=False),
        sa.Column("below_threshold", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("age_bracket_dist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("geography_dist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("language_dist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("interest_dist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("inference_confidence", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_demographics_c_window", "demographic_aggregates_c", ["window_start", "window_end"])
    op.create_index("idx_demographics_c_threshold", "demographic_aggregates_c", ["below_threshold"])

    # 8. Component D: Trend Topics table
    op.create_table(
        "trend_topics_d",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("topic_label", sa.String(length=512), nullable=False),
        sa.Column("topic_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("post_count", sa.Integer(), nullable=False),
        sa.Column("velocity", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("acceleration", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("sample_post_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_trend_topics_d_window", "trend_topics_d", ["window_start", "window_end"])
    op.create_index("idx_trend_topics_d_velocity", "trend_topics_d", ["velocity"])
    op.create_index("idx_trend_topics_d_rank", "trend_topics_d", ["rank"])

    # 9. Component E: Network Nodes table
    op.create_table(
        "network_nodes_e",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=512), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("degree_centrality", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("betweenness_centrality", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("community_id", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("anomaly_score", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("posting_synchrony_signal", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("age_volume_signal", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("duplicate_content_signal", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("coordination_signal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_network_nodes_e_entity_id", "network_nodes_e", ["entity_id"])
    op.create_index("idx_network_nodes_e_window", "network_nodes_e", ["window_start", "window_end"])
    op.create_index("idx_network_nodes_e_betweenness", "network_nodes_e", ["betweenness_centrality"])
    op.create_index("idx_network_nodes_e_anomaly", "network_nodes_e", ["anomaly_score"])
    op.create_index("idx_network_nodes_e_coordination", "network_nodes_e", ["coordination_signal"])

    # 10. Component E: Network Edges table
    op.create_table(
        "network_edges_e",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_entity_id", sa.String(length=255), nullable=False),
        sa.Column("target_entity_id", sa.String(length=255), nullable=False),
        sa.Column("interaction_type", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_network_edges_e_window", "network_edges_e", ["window_start", "window_end"])
    op.create_index("idx_network_edges_e_source", "network_edges_e", ["source_entity_id"])
    op.create_index("idx_network_edges_e_target", "network_edges_e", ["target_entity_id"])

    # 11. RAG Documents table
    op.create_table(
        "rag_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_component", sa.String(length=8), nullable=False),
        sa.Column("source_record_id", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_rag_documents_created_at", "rag_documents", ["created_at"])
    op.create_index("idx_rag_documents_component", "rag_documents", ["source_component"])
    # HNSW Cosine Index on embedding vector
    op.execute("CREATE INDEX IF NOT EXISTS idx_rag_documents_hnsw ON rag_documents USING hnsw (embedding vector_cosine_ops);")

    # 12. RAG Query Log table
    op.create_table(
        "rag_query_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("retrieved_doc_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("relevance_grade", sa.String(length=16), nullable=False),
        sa.Column("llm_provider", sa.String(length=64), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("cited_source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_rating", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("is_grounded", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("queried_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_rag_query_log_queried_at", "rag_query_log", ["queried_at"])


def downgrade() -> None:
    op.drop_table("rag_query_log")
    op.drop_table("rag_documents")
    op.drop_table("network_edges_e")
    op.drop_table("network_nodes_e")
    op.drop_table("trend_topics_d")
    op.drop_table("demographic_aggregates_c")
    op.drop_table("sentiment_results_b")
    op.drop_table("raw_authors")
    op.drop_table("raw_posts")
    op.drop_table("ingestion_runs")
    op.drop_table("monitored_channels")
    op.execute("DROP EXTENSION IF EXISTS vector;")
