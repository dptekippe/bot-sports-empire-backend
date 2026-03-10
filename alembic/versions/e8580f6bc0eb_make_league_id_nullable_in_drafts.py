"""make_league_id_nullable_in_drafts

Revision ID: e8580f6bc0eb
Revises: 2410ea4c40c0
Create Date: 2026-02-01 14:37:28.079749

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8580f6bc0eb'
down_revision: Union[str, Sequence[str], None] = '2410ea4c40c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make league_id nullable in drafts table
    # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
    # For simplicity, we'll use batch operations
    with op.batch_alter_table('drafts') as batch_op:
        batch_op.alter_column('league_id', nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Make league_id non-nullable again
    with op.batch_alter_table('drafts') as batch_op:
        batch_op.alter_column('league_id', nullable=False)
