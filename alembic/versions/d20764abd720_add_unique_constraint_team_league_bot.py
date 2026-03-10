"""add_unique_constraint_team_league_bot

Revision ID: d20764abd720
Revises: 36326dcca49f
Create Date: 2026-01-31 14:55:32.595805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd20764abd720'
down_revision: Union[str, Sequence[str], None] = '36326dcca49f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite doesn't support ALTER TABLE for constraints, use batch mode
    with op.batch_alter_table('teams') as batch_op:
        batch_op.create_unique_constraint('uq_team_league_bot', ['league_id', 'bot_id'])
    
    # Note: SQLite doesn't support ALTER COLUMN to add NOT NULL constraint
    # The season_year NOT NULL constraint is enforced at application level


def downgrade() -> None:
    """Downgrade schema."""
    # SQLite doesn't support ALTER TABLE for constraints, use batch mode
    with op.batch_alter_table('teams') as batch_op:
        batch_op.drop_constraint('uq_team_league_bot', type_='unique')
    
    # Note: SQLite doesn't support ALTER COLUMN to remove NOT NULL constraint
