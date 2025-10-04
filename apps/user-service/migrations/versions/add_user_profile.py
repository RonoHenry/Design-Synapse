"""Add user_profile table.

Revision ID: add_user_profile
Revises: 20eb6872f89d
Create Date: 2025-09-26 11:12:13.374135

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_user_profile"
down_revision: Union[str, None] = "20eb6872f89d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_profiles table."""
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("organization", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("social_links", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column("preferences", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Grant permissions to design_synapse_user
    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE, DELETE ON user_profiles TO design_synapse_user;
        GRANT USAGE, SELECT ON SEQUENCE user_profiles_id_seq TO design_synapse_user;
        """
    )


def downgrade() -> None:
    """Drop user_profiles table."""
    op.drop_table("user_profiles")
