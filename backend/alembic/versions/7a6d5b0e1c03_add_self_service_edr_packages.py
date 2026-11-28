"""add self service edr packages

Revision ID: 7a6d5b0e1c03
Revises: 7a6d5b0e1c02
Create Date: 2026-11-28 15:00:00.000000

Self Service, EDR installer packages, Level 1 (TMGS): ``self_service_edr_packages`` keeps each
package a customer issues itself, with its platform, group, install cap and expiry. Records only:
neither the expiry nor the cap is enforced on the monitoring server yet, and the status is computed
when read. Hard FK to ``customers`` with ON DELETE CASCADE, so deleting a customer is not blocked.
The Sensor table of the design is deferred and not created here.
"""

from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a6d5b0e1c03"
down_revision: Union[str, None] = "7a6d5b0e1c02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "self_service_edr_packages",
        sa.Column("id", sa.String(length=20), nullable=False),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("arch", sa.String(length=16), nullable=False),
        sa.Column("group", sa.String(length=64), nullable=False),
        sa.Column("max_installs", sa.Integer(), nullable=False),
        sa.Column("enrolled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_self_service_edr_packages_customer_code", "self_service_edr_packages", ["customer_code"])


def downgrade() -> None:
    # Dropping the table drops its index; MySQL refuses to drop an index alone while a foreign
    # key relies on it.
    op.drop_table("self_service_edr_packages")
