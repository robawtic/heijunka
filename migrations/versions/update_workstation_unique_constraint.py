"""Update workstation unique constraint

Revision ID: c8f2a1b4d5e6
Revises: b8da5cc1614e
Create Date: 2025-05-28 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f2a1b4d5e6'
down_revision: Union[str, None] = 'b8da5cc1614e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the existing unique constraint on name
    op.drop_constraint('uq_workstations_name', 'workstations', type_='unique')

    # Add a new composite unique constraint on (name, team_id)
    op.create_unique_constraint('uq_workstations_name_team_id', 'workstations', ['name', 'team_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the composite unique constraint
    op.drop_constraint('uq_workstations_name_team_id', 'workstations', type_='unique')

    # Re-add the original unique constraint on name
    op.create_unique_constraint('uq_workstations_name', 'workstations', ['name'])
