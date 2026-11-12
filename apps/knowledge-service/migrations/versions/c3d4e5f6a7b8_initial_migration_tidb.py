"""initial_migration_tidb

Revision ID: c3d4e5f6a7b8
Revises: 
Create Date: 2025-10-08 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create resources table
    op.create_table('resources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=False),
    sa.Column('content_type', sa.String(length=50), nullable=False),
    sa.Column('source_url', sa.String(length=500), nullable=False),
    sa.Column('source_platform', sa.String(length=100), nullable=True),
    sa.Column('vector_embedding', sa.JSON(), nullable=True),
    sa.Column('author', sa.String(length=255), nullable=True),
    sa.Column('publication_date', sa.DateTime(), nullable=True),
    sa.Column('doi', sa.String(length=100), nullable=True),
    sa.Column('license_type', sa.String(length=100), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('key_takeaways', sa.JSON(), nullable=True),
    sa.Column('keywords', sa.JSON(), nullable=True),
    sa.Column('storage_path', sa.String(length=500), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
    sa.PrimaryKeyConstraint('id')
    )

    # Create topics table
    op.create_table('topics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['topics.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )

    # Create bookmarks table
    op.create_table('bookmarks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('resource_id', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    sa.CheckConstraint('user_id > 0', name='check_user_id_positive'),
    sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'resource_id', name='unique_user_resource')
    )

    # Create citations table
    op.create_table('citations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('resource_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('context', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    sa.Column('created_by', sa.Integer(), nullable=False, server_default='1'),
    sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # Create resource_topics junction table
    op.create_table('resource_topics',
    sa.Column('resource_id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], ),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
    sa.PrimaryKeyConstraint('resource_id', 'topic_id')
    )


def downgrade() -> None:
    op.drop_table('resource_topics')
    op.drop_table('citations')
    op.drop_table('bookmarks')
    op.drop_table('topics')
    op.drop_table('resources')
