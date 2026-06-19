"""init schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("discord_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("current_dkp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "auctions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("min_bid", sa.Integer(), nullable=False),
        sa.Column("bid_step", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("winner_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("winning_bid", sa.Integer(), nullable=True),
        sa.Column("started_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("officer_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_transactions_player_created", "transactions", ["player_id", "created_at"])

    op.create_table(
        "bids",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("auction_id", sa.Integer(), sa.ForeignKey("auctions.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_bids_auction_created", "bids", ["auction_id", "created_at"])

    op.create_table(
        "loot_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("auction_id", sa.Integer(), sa.ForeignKey("auctions.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("loot_history")
    op.drop_table("bids")
    op.drop_index("ix_transactions_player_created", "transactions")
    op.drop_table("transactions")
    op.drop_table("auctions")
    op.drop_table("players")
