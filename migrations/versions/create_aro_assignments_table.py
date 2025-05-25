from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'aro_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('from_team_id', sa.Integer(), nullable=False),
        sa.Column('to_team_id', sa.Integer(), nullable=False),
        sa.Column('assignment_date', sa.Date(), nullable=False),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['from_team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['to_team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster lookups
    op.create_index(
        'ix_aro_assignments_date_employee', 
        'aro_assignments', 
        ['assignment_date', 'employee_id']
    )

def downgrade():
    op.drop_index('ix_aro_assignments_date_employee', 'aro_assignments')
    op.drop_table('aro_assignments')