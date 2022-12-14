"""Improve messages

Revision ID: 44db9a31daf9
Revises: 4fe8075c926d
Create Date: 2022-10-15 15:56:34.940597

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "44db9a31daf9"
down_revision = "4fe8075c926d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("messages", sa.Column("message", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("views", sa.BigInteger(), nullable=True))
    op.add_column("messages", sa.Column("forwards", sa.BigInteger(), nullable=True))
    op.add_column("messages", sa.Column("from_id", sa.BigInteger(), nullable=True))
    op.add_column("messages", sa.Column("post_author", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("fwd_from_id", sa.BigInteger(), nullable=True))
    op.add_column("messages", sa.Column("fwd_from_name", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("fwd_post_author", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("message_utc", sa.TIMESTAMP(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("messages", "message_utc")
    op.drop_column("messages", "fwd_post_author")
    op.drop_column("messages", "fwd_from_name")
    op.drop_column("messages", "fwd_from_id")
    op.drop_column("messages", "post_author")
    op.drop_column("messages", "from_id")
    op.drop_column("messages", "forwards")
    op.drop_column("messages", "views")
    op.drop_column("messages", "message")
    # ### end Alembic commands ###
