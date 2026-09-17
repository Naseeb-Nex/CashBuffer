"""Add tx_hash to Transaction

Revision ID: 3185361f564b
Revises: 326e85a8fea9
Create Date: 2026-09-18 01:50:16.541650

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3185361f564b"
down_revision: Union[str, Sequence[str], None] = "326e85a8fea9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("tx_hash", sa.String(), nullable=True))
    op.create_index("ix_transactions_tx_hash", "transactions", ["tx_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_transactions_tx_hash", table_name="transactions")
    op.drop_column("transactions", "tx_hash")
