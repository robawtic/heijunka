"""create_aro_assignments_table

Revision ID: 342a1c9f0f7a
Revises: update_employee_availability
Create Date: 2025-05-26 12:00:00

"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '342a1c9f0f7a'
down_revision = 'update_employee_availability'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'aro_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('from_team_id', sa.Integer(), nullable=False),
        sa.Column('to_team_id', sa.Integer(), nullable=False),
        sa.Column('assignment_date', sa.Date(), nullable=False),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.ForeignKeyConstraint(['from_team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['to_team_id'], ['teams.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_aro_assignments_date_employee', 
        'aro_assignments', 
        ['assignment_date', 'employee_id']
    )

def downgrade():
    op.drop_index('ix_aro_assignments_date_employee', 'aro_assignments')
    op.drop_table('aro_assignments')