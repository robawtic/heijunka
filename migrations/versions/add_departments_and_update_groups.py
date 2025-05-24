"""add departments and update groups

Revision ID: add_departments_and_update_groups
Revises: add_description_and_timestamps_to_teams
Create Date: 2025-05-23 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_departments_and_update_groups'
down_revision = 'add_description_and_timestamps_to_teams'
branch_labels = None
depends_on = None


def upgrade():
    # Create departments table
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Add department_id column to groups table
    op.add_column('groups', sa.Column('department_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_groups_department_id_departments',
        'groups', 'departments',
        ['department_id'], ['id']
    )


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_groups_department_id_departments', 'groups', type_='foreignkey')
    
    # Drop department_id column from groups table
    op.drop_column('groups', 'department_id')
    
    # Drop departments table
    op.drop_table('departments')