"""Add batch_jobs table for enhanced batch processing

Revision ID: batch_jobs_001
Revises: c3d4e5f6a7b8
Create Date: 2024-01-01 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "batch_jobs_001"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    """Create batch_jobs table for enhanced batch processing capabilities."""
    op.create_table(
        "batch_jobs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("total_files", sa.Integer, nullable=False),
        sa.Column("processed_files", sa.Integer, default=0),
        sa.Column("successful_files", sa.Integer, default=0),
        sa.Column("failed_files", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("processing_time_seconds", sa.Float, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata", sa.Text, nullable=True),  # JSON metadata
        sa.Column("priority", sa.Integer, default=0),  # Higher number = higher priority
        sa.Column("retry_count", sa.Integer, default=0),
        sa.Column("max_retries", sa.Integer, default=3),
        sa.Column("progress_callback_url", sa.String(500), nullable=True),
        sa.Column("user_id", sa.Integer, nullable=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # Create indexes for better query performance
    op.create_index("idx_batch_jobs_status", "batch_jobs", ["status"])
    op.create_index("idx_batch_jobs_created_at", "batch_jobs", ["created_at"])
    op.create_index("idx_batch_jobs_user_id", "batch_jobs", ["user_id"])
    op.create_index("idx_batch_jobs_priority", "batch_jobs", ["priority"])
    op.create_index(
        "idx_batch_jobs_status_priority", "batch_jobs", ["status", "priority"]
    )


def downgrade():
    """Drop batch_jobs table."""
    op.drop_index("idx_batch_jobs_status_priority", "batch_jobs")
    op.drop_index("idx_batch_jobs_priority", "batch_jobs")
    op.drop_index("idx_batch_jobs_user_id", "batch_jobs")
    op.drop_index("idx_batch_jobs_created_at", "batch_jobs")
    op.drop_index("idx_batch_jobs_status", "batch_jobs")
    op.drop_table("batch_jobs")
