"""Update employee availability to use status enum

Revision ID: update_employee_availability_status
Revises: add_dept_groups
Create Date: 2025-05-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import sqlite
from domain.value_objects.employee_availability import AvailabilityStatus

# revision identifiers, used by Alembic.
revision = '9b2afc1d0ef4'
down_revision = '342a1c9f0f7a'  # This is the revision ID of create_aro_assignments_table.py
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if the table already has the status column (meaning the previous migration was applied)
    if 'employee_availability' in inspector.get_table_names():
        columns = inspector.get_columns('employee_availability')
        column_names = [col['name'] for col in columns]
        if 'status' in column_names:
            print("Table employee_availability already has status column — skipping migration.")
            return

    # Check if the temporary table exists from a previous failed migration
    if 'employee_availability_new' in inspector.get_table_names():
        print("Dropping existing employee_availability_new table from previous failed migration.")
        op.drop_table('employee_availability_new')

    # Create a temporary table with the new schema
    try:
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
                   SELECT id,
                          employee_id, date, period, CASE
                       WHEN is_call_in = true THEN 'CALL_IN'::availabilitystatus
                       WHEN is_aro = true THEN 'ARO'::availabilitystatus
                       WHEN is_partial = true THEN 'PARTIAL'::availabilitystatus
                       WHEN is_offline = true THEN 'OFFLINE'::availabilitystatus
                       ELSE 'AVAILABLE'::availabilitystatus
                   END
                   FROM employee_availability
                   """)

        # Drop the old table
        op.drop_table('employee_availability')

        # Rename the new table to the original name
        op.rename_table('employee_availability_new', 'employee_availability')

    except Exception as e:
        print(f"Error during migration: {e}")
        # If the table was created but migration failed, clean up
        if 'employee_availability_new' in inspector.get_table_names():
            op.drop_table('employee_availability_new')
        raise




def downgrade():
    # Create a temporary table with the old schema
    op.create_table(
        'employee_availability_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.Column('is_partial', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_call_in', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_aro', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_offline', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Copy data from the new table to the old table, converting status enum to boolean flags
    op.execute("""
    INSERT INTO employee_availability_old (id, employee_id, date, period, is_partial, is_call_in, is_aro, is_offline)
    SELECT id, employee_id, date, period,
        CASE WHEN status = 'PARTIAL' THEN true ELSE false END,
        CASE WHEN status = 'CALL_IN' THEN true ELSE false END,
        CASE WHEN status = 'ARO' THEN true ELSE false END,
        CASE WHEN status = 'OFFLINE' THEN true ELSE false END
    FROM employee_availability
    """)

    # Drop the new table
    op.drop_table('employee_availability')

    # Rename the old table to the original name
    op.rename_table('employee_availability_old', 'employee_availability')
