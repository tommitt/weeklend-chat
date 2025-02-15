"""Event URL is mandatory

Revision ID: 78376c1ee1c0
Revises: f515b814eb46
Create Date: 2024-01-07 19:02:32.370229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78376c1ee1c0'
down_revision: Union[str, None] = 'f515b814eb46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('events', 'url',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('events', 'url',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###
