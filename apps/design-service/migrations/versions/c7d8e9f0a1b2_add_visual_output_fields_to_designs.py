"""Add visual output fields to designs table

Revision ID: c7d8e9f0a1b2
Revises: b6576f89ece0
Create Date: 2025-01-21 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = 'b6576f89ece0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add visual output fields to designs table."""
    # Add visual output URL fields
    op.add_column('designs', sa.Column('floor_plan_url', sa.String(length=500), nullable=True))
    op.add_column('designs', sa.Column('rendering_url', sa.String(length=500), nullable=True))
    op.add_column('designs', sa.Column('model_file_url', sa.String(length=500), nullable=True))
    
    # Add visual generation status and metadata fields
    op.add_column('designs', sa.Column('visual_generation_status', sa.String(length=50), nullable=False, server_default='pending'))
    op.add_column('designs', sa.Column('visual_generation_error', sa.Text(), nullable=True))
    op.add_column('designs', sa.Column('visual_generated_at', sa.DateTime(), nullable=True))
    
    # Add index on visual_generation_status for performance
    op.create_index(op.f('ix_designs_visual_generation_status'), 'designs', ['visual_generation_status'], unique=False)


def downgrade() -> None:
    """Remove visual output fields from designs table."""
    # Drop index first
    op.drop_index(op.f('ix_designs_visual_generation_status'), table_name='designs')
    
    # Drop visual output fields
    op.drop_column('designs', 'visual_generated_at')
    op.drop_column('designs', 'visual_generation_error')
    op.drop_column('designs', 'visual_generation_status')
    op.drop_column('designs', 'model_file_url')
    op.drop_column('designs', 'rendering_url')
    op.drop_column('designs', 'floor_plan_url')