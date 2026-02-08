"""veto_voting_system_migration

Revision ID: veto_voting_system
Revises: 73631f523061
Create Date: 2026-01-31 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'veto_voting_system'
down_revision: Union[str, Sequence[str], None] = '73631f523061'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for veto-based voting system."""
    # Rename votes_required column to veto_votes_required
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.alter_column(
            'votes_required',
            new_column_name='veto_votes_required',
            existing_type=sa.Integer(),
            existing_nullable=True,
            server_default='1'
        )
    
    # Set default value for any null values
    op.execute("UPDATE transactions SET veto_votes_required = 1 WHERE veto_votes_required IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Rename back to votes_required
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.alter_column(
            'veto_votes_required',
            new_column_name='votes_required',
            existing_type=sa.Integer(),
            existing_nullable=True,
            server_default='0'
        )
    
    # Set default value back
    op.execute("UPDATE transactions SET votes_required = 0 WHERE votes_required IS NULL")