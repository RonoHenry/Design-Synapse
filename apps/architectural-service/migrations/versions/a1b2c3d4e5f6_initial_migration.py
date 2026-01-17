"""Initial migration with all models

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-01-15 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create designs table
    op.create_table(
        "designs",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("project_id", mysql.CHAR(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("building_type", sa.String(50), nullable=False),
        sa.Column("location_data", sa.JSON(), nullable=False),
        sa.Column(
            "current_version", sa.String(20), nullable=False, server_default="1.0"
        ),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("design_metadata", sa.JSON(), nullable=False),
        sa.Column("created_by", mysql.CHAR(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_design_project", "project_id"),
        sa.Index("idx_design_deleted", "is_deleted"),
        sa.Index("idx_design_status", "status"),
        sa.Index("idx_design_created", "created_at"),
        comment="Architectural design documents with version control",
    )

    # Create design_versions table
    op.create_table(
        "design_versions",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("design_data", sa.JSON(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", mysql.CHAR(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_design_version", "design_id", "version"),
        sa.Index("idx_design_version_number", "design_id", "version_number"),
        sa.UniqueConstraint(
            "design_id", "version_number", name="uq_design_version_number"
        ),
        comment="Version history for design documents",
    )

    # Create drawings table
    op.create_table(
        "drawings",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("design_version", sa.String(20), nullable=False),
        sa.Column("drawing_type", sa.String(50), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("scale", sa.String(50), nullable=True),
        sa.Column("sheet_number", sa.String(50), nullable=True),
        sa.Column("drawing_metadata", sa.JSON(), nullable=False),
        sa.Column("created_by", mysql.CHAR(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_design_drawings", "design_id", "drawing_type"),
        sa.Index("idx_drawing_type", "drawing_type"),
        sa.Index("idx_drawing_created", "created_at"),
        comment="Architectural drawings associated with designs",
    )

    # Create compliance_checks table
    op.create_table(
        "compliance_checks",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("design_version", sa.String(20), nullable=False),
        sa.Column("code_standards", sa.JSON(), nullable=False),
        sa.Column("jurisdiction", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("violations", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("report_url", sa.String(500), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_design_compliance", "design_id", "status"),
        sa.Index("idx_compliance_status", "status"),
        sa.Index("idx_compliance_started", "started_at"),
        comment="Building code compliance check results",
    )

    # Create structural_analyses table
    op.create_table(
        "structural_analyses",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("design_version", sa.String(20), nullable=False),
        sa.Column("structural_system", sa.String(100), nullable=False),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("load_calculations", sa.JSON(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("report_url", sa.String(500), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_design_structural", "design_id", "status"),
        sa.Index("idx_structural_status", "status"),
        sa.Index("idx_structural_started", "started_at"),
        comment="Structural analysis results",
    )

    # Create material_specifications table
    op.create_table(
        "material_specifications",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("material_type", sa.String(100), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("vendor_material_id", mysql.CHAR(36), nullable=True),
        sa.Column("vendor_info", sa.JSON(), nullable=True),
        sa.Column("cost_estimate", sa.Numeric(12, 2), nullable=True),
        sa.Column("design_elements", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_design_materials", "design_id", "category"),
        sa.Index("idx_material_category", "category"),
        sa.Index("idx_material_type", "material_type"),
        comment="Material specifications for designs",
    )

    # Create space_planning table
    op.create_table(
        "space_planning",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("space_program", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_design_space_planning", "design_id", "status"),
        sa.Index("idx_space_planning_status", "status"),
        comment="Space planning analysis results",
    )

    # Create accessibility_checks table
    op.create_table(
        "accessibility_checks",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("design_version", sa.String(20), nullable=False),
        sa.Column("standards", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("violations", sa.JSON(), nullable=False),
        sa.Column("accessible_routes", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_design_accessibility", "design_id", "status"),
        sa.Index("idx_accessibility_status", "status"),
        comment="Accessibility compliance check results",
    )

    # Create energy_analyses table
    op.create_table(
        "energy_analyses",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("design_version", sa.String(20), nullable=False),
        sa.Column("standards", sa.JSON(), nullable=False),
        sa.Column("climate_zone", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("envelope_performance", sa.JSON(), nullable=False),
        sa.Column("energy_consumption", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("certificate_url", sa.String(500), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_design_energy", "design_id", "status"),
        sa.Index("idx_energy_status", "status"),
        comment="Energy efficiency analysis results",
    )

    # Create collaboration_sessions table
    op.create_table(
        "collaboration_sessions",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("design_id", mysql.CHAR(36), nullable=False),
        sa.Column("active_users", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.Index("idx_active_sessions", "design_id", "is_active"),
        sa.Index("idx_session_created", "created_at"),
        comment="Real-time collaboration sessions",
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table("collaboration_sessions")
    op.drop_table("energy_analyses")
    op.drop_table("accessibility_checks")
    op.drop_table("space_planning")
    op.drop_table("material_specifications")
    op.drop_table("structural_analyses")
    op.drop_table("compliance_checks")
    op.drop_table("drawings")
    op.drop_table("design_versions")
    op.drop_table("designs")
