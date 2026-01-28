"""Add country column to users table

Revision ID: add_country_column
Revises: d1b85769b183
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_country_column'
down_revision: Union[str, None] = 'd1b85769b183'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add country column to users table."""
    # Check if country column exists before adding
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add country column if it doesn't exist
    if 'country' not in columns:
        op.add_column('users', sa.Column('country', sa.String(length=10), nullable=True))
        # Add index on country column
        op.create_index('ix_users_country', 'users', ['country'], unique=False)
    
    # Add git_username column if it doesn't exist
    if 'git_username' not in columns:
        op.add_column('users', sa.Column('git_username', sa.String(length=255), nullable=True))
        op.create_index('ix_users_git_username', 'users', ['git_username'], unique=True)


def downgrade() -> None:
    """Remove country column from users table."""
    # Remove index
    op.drop_index('ix_users_country', table_name='users')
    # Remove country column
    op.drop_column('users', 'country')

