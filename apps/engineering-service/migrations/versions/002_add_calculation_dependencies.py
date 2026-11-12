"""add calculation dependencies table

Revision ID: 002_dependencies
Revises: 001_initial
Create Date: 2024-01-15 11:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_dependencies"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create calculation_dependencies table for tracking dependencies."""
    op.create_table(
        "calculation_dependencies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_calculation_id", sa.Integer(), nullable=False),
        sa.Column("target_calculation_id", sa.Integer(), nullable=False),
        sa.Column("dependency_type", sa.String(length=100), nullable=False),
        sa.Column("dependent_field", sa.String(length=255), nullable=True),
        sa.Column("source_field", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["source_calculation_id"],
            ["calculation_sheets.id"],
            name="fk_calc_dep_source",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_calculation_id"],
            ["calculation_sheets.id"],
            name="fk_calc_dep_target",
            ondelete="CASCADE",
        ),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_calculation_dependencies_source_calculation_id",
        "calculation_dependencies",
        ["source_calculation_id"],
    )
    op.create_index(
        "ix_calculation_dependencies_target_calculation_id",
        "calculation_dependencies",
        ["target_calculation_id"],
    )

    # Create composite index for unique constraint
    op.create_index(
        "ix_calculation_dependencies_source_target",
        "calculation_dependencies",
        ["source_calculation_id", "target_calculation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop calculation_dependencies table."""
    op.drop_index(
        "ix_calculation_dependencies_source_target",
        table_name="calculation_dependencies",
    )
    op.drop_index(
        "ix_calculation_dependencies_target_calculation_id",
        table_name="calculation_dependencies",
    )
    op.drop_index(
        "ix_calculation_dependencies_source_calculation_id",
        table_name="calculation_dependencies",
    )
    op.drop_table("calculation_dependencies")
