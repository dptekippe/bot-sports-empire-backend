"""add_name_to_drafts

Revision ID: 2410ea4c40c0
Revises: 20250201_add_sleeper_fields
Create Date: 2026-02-01 14:35:53.114913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2410ea4c40c0'
down_revision: Union[str, Sequence[str], None] = '20250201_add_sleeper_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add name column to drafts table
    op.add_column('drafts', sa.Column('name', sa.String(length=255), nullable=False, server_default='Untitled Draft'))
    
    # Create index on name for faster searches
    op.create_index(op.f('ix_drafts_name'), 'drafts', ['name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index(op.f('ix_drafts_name'), table_name='drafts')
    
    # Drop name column
    op.drop_column('drafts', 'name')
