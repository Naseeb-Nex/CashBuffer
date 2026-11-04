"""Add QuarantinedEmail

Revision ID: 4125361f564c
Revises: 3185361f564b
Create Date: 2026-09-18 01:50:16.541650

"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "4125361f564c"
down_revision: Union[str, Sequence[str], None] = "3185361f564b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quarantined_emails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("email_text", sa.String(), nullable=False),
        sa.Column("error_reason", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("resolved", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quarantined_emails_user_id"), "quarantined_emails", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_quarantined_emails_user_id"), table_name="quarantined_emails")
    op.drop_table("quarantined_emails")
