"""Add external_adp field to players and create draft_history table

Revision ID: add_external_adp_and_draft_history
Revises: e8580f6bc0eb
Create Date: 2026-02-01 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_external_adp_and_draft_history'
down_revision = 'e8580f6bc0eb'
branch_labels = None
depends_on = None


def upgrade():
    # Add external_adp field to players table
    op.add_column('players', sa.Column('external_adp', sa.Float(), nullable=True))
    op.add_column('players', sa.Column('external_adp_source', sa.String(), nullable=True))
    op.add_column('players', sa.Column('external_adp_updated_at', sa.DateTime(), nullable=True))
    
    # Create draft_history table
    op.create_table('draft_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.String(), nullable=False),
        sa.Column('draft_year', sa.Integer(), nullable=False),
        sa.Column('draft_type', sa.String(), nullable=False),  # 'internal' or 'external'
        sa.Column('league_id', sa.String(), nullable=True),  # For internal drafts
        sa.Column('draft_id', sa.String(), nullable=True),  # For internal drafts
        sa.Column('pick_number', sa.Integer(), nullable=True),
        sa.Column('round', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.String(), nullable=True),
        sa.Column('adp_value', sa.Float(), nullable=True),
        sa.Column('adp_source', sa.String(), nullable=True),  # 'ffc', 'sleeper', 'espn', etc.
        sa.Column('scoring_format', sa.String(), nullable=True),  # 'ppr', 'half', 'standard'
        sa.Column('team_count', sa.Integer(), nullable=True),  # 8, 10, 12, 14
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['player_id'], ['players.player_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_draft_history_player_id'), 'draft_history', ['player_id'], unique=False)
    op.create_index(op.f('ix_draft_history_draft_year'), 'draft_history', ['draft_year'], unique=False)
    op.create_index(op.f('ix_draft_history_draft_type'), 'draft_history', ['draft_type'], unique=False)
    op.create_index(op.f('ix_draft_history_adp_source'), 'draft_history', ['adp_source'], unique=False)
    
    # Create composite index for common queries
    op.create_index('ix_draft_history_player_year_source', 'draft_history', 
                   ['player_id', 'draft_year', 'adp_source'], unique=False)


def downgrade():
    # Drop draft_history table
    op.drop_table('draft_history')
    
    # Remove columns from players table
    op.drop_column('players', 'external_adp_updated_at')
    op.drop_column('players', 'external_adp_source')
    op.drop_column('players', 'external_adp')