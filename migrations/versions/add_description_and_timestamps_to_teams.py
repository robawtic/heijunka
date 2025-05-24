"""Add description and timestamps to teams table

Revision ID: add_description_and_timestamps
Revises: add_is_temporary
Create Date: 2025-05-22 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'add_description_and_timestamps'
down_revision: Union[str, None] = 'add_is_temporary'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add description and timestamps columns to teams table."""
    # Add the description column
    op.add_column('teams', sa.Column('description', sa.String(), nullable=True))
    
    # Add the created_at column with current timestamp as default
    op.add_column('teams', sa.Column('created_at', sa.DateTime(), nullable=True, 
                                     server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Add the updated_at column with current timestamp as default
    op.add_column('teams', sa.Column('updated_at', sa.DateTime(), nullable=True,
                                     server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Create an index on created_at for better query performance
    op.create_index(op.f('ix_teams_created_at'), 'teams', ['created_at'], unique=False)


def downgrade() -> None:
    """Remove description and timestamps columns from teams table."""
    # Drop the index
    op.drop_index(op.f('ix_teams_created_at'), table_name='teams')
    
    # Drop the columns
    op.drop_column('teams', 'updated_at')
    op.drop_column('teams', 'created_at')
    op.drop_column('teams', 'description')