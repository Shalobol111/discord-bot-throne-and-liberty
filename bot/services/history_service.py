from sqlalchemy import desc, select

from bot.database.engine import session_maker
from bot.database.models import LootHistory, Player, Transaction, TxType
from bot.services.dtos import LootDTO, PlayerDTO, TransactionDTO


def _player_to_dto(p: Player) -> PlayerDTO:
    return PlayerDTO(
        discord_id=p.discord_id,
        display_name=p.display_name,
        current_dkp=p.current_dkp,
        total_earned=p.total_earned,
        total_spent=p.total_spent,
    )


def _tx_to_dto(t: Transaction) -> TransactionDTO:
    return TransactionDTO(
        id=t.id,
        amount=t.amount,
        balance_after=t.balance_after,
        type=TxType(t.type),
        reason=t.reason,
        officer_id=t.officer_id,
        created_at=t.created_at,
    )


async def get_player_overview(
    discord_id: int, display_name: str
) -> tuple[PlayerDTO | None, list[TransactionDTO]]:
    async with session_maker() as session:
        result = await session.execute(select(Player).where(Player.discord_id == discord_id))
        player = result.scalar_one_or_none()
        if player is None:
            return None, []

        tx_result = await session.execute(
            select(Transaction)
            .where(Transaction.player_id == player.id)
            .order_by(desc(Transaction.created_at))
            .limit(10)
        )
        transactions = tx_result.scalars().all()
        return _player_to_dto(player), [_tx_to_dto(t) for t in transactions]


async def get_top(limit: int = 10) -> list[PlayerDTO]:
    async with session_maker() as session:
        result = await session.execute(
            select(Player).order_by(desc(Player.current_dkp)).limit(limit)
        )
        players = result.scalars().all()
        return [_player_to_dto(p) for p in players]


async def get_history(discord_id: int, limit: int = 10) -> tuple[str | None, list[TransactionDTO]]:
    async with session_maker() as session:
        p_result = await session.execute(select(Player).where(Player.discord_id == discord_id))
        player = p_result.scalar_one_or_none()
        if player is None:
            return None, []

        tx_result = await session.execute(
            select(Transaction)
            .where(Transaction.player_id == player.id)
            .order_by(desc(Transaction.created_at))
            .limit(limit)
        )
        transactions = tx_result.scalars().all()
        return player.display_name, [_tx_to_dto(t) for t in transactions]


async def get_loot(limit: int = 10) -> list[LootDTO]:
    async with session_maker() as session:
        result = await session.execute(
            select(LootHistory, Player)
            .join(Player, LootHistory.player_id == Player.id)
            .order_by(desc(LootHistory.created_at))
            .limit(limit)
        )
        rows = result.all()
        return [
            LootDTO(
                item_name=loot.item_name,
                winner_name=player.display_name,
                winner_discord_id=player.discord_id,
                cost=loot.cost,
                created_at=loot.created_at,
            )
            for loot, player in rows
        ]
