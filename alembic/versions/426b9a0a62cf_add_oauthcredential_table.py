"""Add OAuthCredential table

Revision ID: 426b9a0a62cf
Revises: 4125361f564c
Create Date: 2026-09-18 06:59:39.173572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '426b9a0a62cf'
down_revision: Union[str, Sequence[str], None] = '4125361f564c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('oauth_credentials',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('encrypted_access_token', sa.String(), nullable=False),
        sa.Column('encrypted_refresh_token', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_oauth_credentials_user_id'), 'oauth_credentials', ['user_id'], unique=False)
    op.create_index(op.f('ix_oauth_credentials_provider'), 'oauth_credentials', ['provider'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_oauth_credentials_provider'), table_name='oauth_credentials')
    op.drop_index(op.f('ix_oauth_credentials_user_id'), table_name='oauth_credentials')
    op.drop_table('oauth_credentials')
