"""Add content analysis fields to resources table

Revision ID: add_content_analysis_fields
Revises: c3d4e5f6a7b8
Create Date: 2024-01-15 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "add_content_analysis_fields"
down_revision = "c3d4e5f6a7b8_initial_migration_tidb"
branch_labels = None
depends_on = None


def upgrade():
    """Add content analysis fields to resources table."""
    # Add new columns for content analysis
    op.add_column(
        "resources", sa.Column("content_classification", sa.String(50), nullable=True)
    )
    op.add_column(
        "resources", sa.Column("complexity_level", sa.String(20), nullable=True)
    )
    op.add_column("resources", sa.Column("technical_domains", sa.JSON(), nullable=True))
    op.add_column(
        "resources", sa.Column("readability_score", sa.Float(), nullable=True)
    )
    op.add_column(
        "resources", sa.Column("estimated_reading_time", sa.Integer(), nullable=True)
    )
    op.add_column("resources", sa.Column("language", sa.String(50), nullable=True))
    op.add_column("resources", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("resources", sa.Column("auto_tags", sa.JSON(), nullable=True))
    op.add_column("resources", sa.Column("analysis_metadata", sa.JSON(), nullable=True))
    op.add_column(
        "resources", sa.Column("analysis_timestamp", sa.DateTime(), nullable=True)
    )


def downgrade():
    """Remove content analysis fields from resources table."""
    op.drop_column("resources", "analysis_timestamp")
    op.drop_column("resources", "analysis_metadata")
    op.drop_column("resources", "auto_tags")
    op.drop_column("resources", "quality_score")
    op.drop_column("resources", "language")
    op.drop_column("resources", "estimated_reading_time")
    op.drop_column("resources", "readability_score")
    op.drop_column("resources", "technical_domains")
    op.drop_column("resources", "complexity_level")
    op.drop_column("resources", "content_classification")
