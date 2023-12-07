"""Introduce pull chat

Revision ID: 4dc3e84d3090
Revises: fd8e31746245
Create Date: 2023-12-07 18:07:46.385789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "4dc3e84d3090"
down_revision: Union[str, None] = "fd8e31746245"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "businesses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("registered_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "business_conversations",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wa_id", sa.String(), nullable=False),
        sa.Column("from_message", sa.String(), nullable=False),
        sa.Column("to_message", sa.String(), nullable=True),
        sa.Column(
            "answer_type",
            postgresql.ENUM(name="answertype", create_type=False),
            nullable=False,
        ),
        sa.Column("used_event_ids", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("registered_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["businesses.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_business_conversations_wa_id"),
        "business_conversations",
        ["wa_id"],
        unique=False,
    )
    op.add_column("events", sa.Column("business_id", sa.Integer(), nullable=True))
    op.create_foreign_key(None, "events", "businesses", ["business_id"], ["id"])
    op.drop_column("events", "is_for_animals")
    op.drop_column("events", "is_for_disabled")
    op.drop_column("events", "is_countryside")
    op.drop_column("events", "is_for_children")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "events",
        sa.Column("is_for_children", sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "events",
        sa.Column("is_countryside", sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "events",
        sa.Column("is_for_disabled", sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "events",
        sa.Column("is_for_animals", sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.drop_constraint(None, "events", type_="foreignkey")
    op.drop_column("events", "business_id")
    op.drop_index(
        op.f("ix_business_conversations_wa_id"), table_name="business_conversations"
    )
    op.drop_table("business_conversations")
    op.drop_table("businesses")
    # ### end Alembic commands ###
