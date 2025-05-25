"""Update employee availability to use status enum

Revision ID: update_employee_availability
Revises: add_departments_and_update_groups
Create Date: 2025-05-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
from domain.value_objects.employee_availability import AvailabilityStatus

# revision identifiers, used by Alembic.
revision = 'update_employee_availability'
down_revision = 'add_departments_and_update_groups'
branch_labels = None
depends_on = None


def upgrade():
    # Create a temporary table with the new schema
    op.create_table(
        'employee_availability_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum(AvailabilityStatus), nullable=False, 
                  server_default=AvailabilityStatus.AVAILABLE.name),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Copy data from the old table to the new table, converting boolean flags to status enum
    op.execute("""
    INSERT INTO employee_availability_new (id, employee_id, date, period, status)
    SELECT id, employee_id, date, period,
        CASE
            WHEN is_call_in = 1 THEN 'CALL_IN'
            WHEN is_aro = 1 THEN 'ARO'
            WHEN is_partial = 1 THEN 'PARTIAL'
            WHEN is_offline = 1 THEN 'OFFLINE'
            ELSE 'AVAILABLE'
        END
    FROM employee_availability
    """)

    # Drop the old table
    op.drop_table('employee_availability')

    # Rename the new table to the original name
    op.rename_table('employee_availability_new', 'employee_availability')


def downgrade():
    # Create a temporary table with the old schema
    op.create_table(
        'employee_availability_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.Column('is_partial', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_call_in', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_aro', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_offline', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Copy data from the new table to the old table, converting status enum to boolean flags
    op.execute("""
    INSERT INTO employee_availability_old (id, employee_id, date, period, is_partial, is_call_in, is_aro, is_offline)
    SELECT id, employee_id, date, period,
        CASE WHEN status = 'PARTIAL' THEN 1 ELSE 0 END,
        CASE WHEN status = 'CALL_IN' THEN 1 ELSE 0 END,
        CASE WHEN status = 'ARO' THEN 1 ELSE 0 END,
        CASE WHEN status = 'OFFLINE' THEN 1 ELSE 0 END
    FROM employee_availability
    """)

    # Drop the new table
    op.drop_table('employee_availability')

    # Rename the old table to the original name
    op.rename_table('employee_availability_old', 'employee_availability')
