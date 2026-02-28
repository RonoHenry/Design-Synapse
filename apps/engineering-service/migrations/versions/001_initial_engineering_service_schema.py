"""initial engineering service schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial engineering service schema."""
    # Create calculation_sheets table
    op.create_table(
        "calculation_sheets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("calculation_type", sa.String(length=100), nullable=False),
        sa.Column("inputs", mysql.JSON(), nullable=False),
        sa.Column("outputs", mysql.JSON(), nullable=False),
        sa.Column("formulas", mysql.JSON(), nullable=True),
        sa.Column("references", mysql.JSON(), nullable=True),
        sa.Column(
            "units", sa.String(length=50), nullable=True, server_default="imperial"
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="draft"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_calculation_sheets_project_id"),
        "calculation_sheets",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calculation_sheets_calculation_type"),
        "calculation_sheets",
        ["calculation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calculation_sheets_parent_id"),
        "calculation_sheets",
        ["parent_id"],
        unique=False,
    )

    # Create structural_designs table
    op.create_table(
        "structural_designs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("calculation_sheet_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("design_type", sa.String(length=50), nullable=False),
        sa.Column("loads", mysql.JSON(), nullable=False),
        sa.Column("material_properties", mysql.JSON(), nullable=False),
        sa.Column("geometry", mysql.JSON(), nullable=False),
        sa.Column("design_results", mysql.JSON(), nullable=False),
        sa.Column("stress_ratios", mysql.JSON(), nullable=False),
        sa.Column("code_references", mysql.JSON(), nullable=True),
        sa.Column(
            "units", sa.String(length=50), nullable=True, server_default="imperial"
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="draft"
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["calculation_sheet_id"],
            ["calculation_sheets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_structural_designs_project_id"),
        "structural_designs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_structural_designs_calculation_sheet_id"),
        "structural_designs",
        ["calculation_sheet_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_structural_designs_design_type"),
        "structural_designs",
        ["design_type"],
        unique=False,
    )

    # Create mep_designs table
    op.create_table(
        "mep_designs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("calculation_sheet_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_type", sa.String(length=50), nullable=False),
        sa.Column("loads", mysql.JSON(), nullable=False),
        sa.Column("equipment", mysql.JSON(), nullable=False),
        sa.Column("distribution", mysql.JSON(), nullable=False),
        sa.Column("sizing_results", mysql.JSON(), nullable=False),
        sa.Column("code_references", mysql.JSON(), nullable=True),
        sa.Column(
            "units", sa.String(length=50), nullable=True, server_default="imperial"
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="draft"
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["calculation_sheet_id"],
            ["calculation_sheets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mep_designs_project_id"),
        "mep_designs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mep_designs_calculation_sheet_id"),
        "mep_designs",
        ["calculation_sheet_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mep_designs_system_type"),
        "mep_designs",
        ["system_type"],
        unique=False,
    )

    # Create civil_designs table
    op.create_table(
        "civil_designs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("calculation_sheet_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("design_type", sa.String(length=50), nullable=False),
        sa.Column("site_parameters", mysql.JSON(), nullable=False),
        sa.Column("design_criteria", mysql.JSON(), nullable=False),
        sa.Column("design_results", mysql.JSON(), nullable=False),
        sa.Column("code_references", mysql.JSON(), nullable=True),
        sa.Column(
            "units", sa.String(length=50), nullable=True, server_default="imperial"
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="draft"
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["calculation_sheet_id"],
            ["calculation_sheets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_civil_designs_project_id"),
        "civil_designs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_civil_designs_calculation_sheet_id"),
        "civil_designs",
        ["calculation_sheet_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_civil_designs_design_type"),
        "civil_designs",
        ["design_type"],
        unique=False,
    )

    # Create compliance_reports table
    op.create_table(
        "compliance_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("calculation_sheet_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("code_type", sa.String(length=50), nullable=False),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("code_version", sa.String(length=50), nullable=False),
        sa.Column("checks_performed", mysql.JSON(), nullable=False),
        sa.Column("violations", mysql.JSON(), nullable=False),
        sa.Column("recommendations", mysql.JSON(), nullable=True),
        sa.Column("overall_status", sa.String(length=20), nullable=False),
        sa.Column("generated_by", sa.String(length=255), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["calculation_sheet_id"],
            ["calculation_sheets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_compliance_reports_project_id"),
        "compliance_reports",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_compliance_reports_calculation_sheet_id"),
        "compliance_reports",
        ["calculation_sheet_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_compliance_reports_code_type"),
        "compliance_reports",
        ["code_type"],
        unique=False,
    )

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("changes", mysql.JSON(), nullable=True),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="success"
        ),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_user_id"),
        "audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_project_id"),
        "audit_logs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_action_type"),
        "audit_logs",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_entity_type"),
        "audit_logs",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_entity_id"),
        "audit_logs",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_timestamp"),
        "audit_logs",
        ["timestamp"],
        unique=False,
    )


def downgrade() -> None:
    """Drop all engineering service tables."""
    op.drop_table("audit_logs")
    op.drop_table("compliance_reports")
    op.drop_table("civil_designs")
    op.drop_table("mep_designs")
    op.drop_table("structural_designs")
    op.drop_table("calculation_sheets")
