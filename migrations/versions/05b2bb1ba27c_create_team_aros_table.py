"""Create team_aros table

Revision ID: 05b2bb1ba27c
Revises: da795f9b121b
Create Date: 2025-06-05 16:32:25.557237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05b2bb1ba27c'
down_revision: Union[str, None] = 'da795f9b121b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create team_aros table
    op.create_table('team_aros',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive')", name=op.f('ck_team_aros_status')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], name=op.f('fk_team_aros_employee_id_employees')),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], name=op.f('fk_team_aros_team_id_teams')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_team_aros'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop team_aros table
    op.drop_table('team_aros')
