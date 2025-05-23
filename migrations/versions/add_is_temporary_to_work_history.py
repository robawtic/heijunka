"""Add is_temporary field to employee_work_history

Revision ID: add_is_temporary
Revises: c75ee1bbbfc0
Create Date: 2025-05-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_is_temporary'
down_revision: Union[str, None] = 'c75ee1bbbfc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_temporary column to employee_work_history table."""
    # Add the is_temporary column with a default value of False
    op.add_column('employee_work_history', sa.Column('is_temporary', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove is_temporary column from employee_work_history table."""
    # Drop the is_temporary column
    op.drop_column('employee_work_history', 'is_temporary')