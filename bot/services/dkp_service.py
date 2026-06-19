from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.engine import session_maker
from bot.database.models import Player, Transaction, TxType
from bot.services.dtos import DecayResult, DkpChangeResult, PlayerDTO, TransactionDTO
from bot.services.exceptions import InsufficientDKPError


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


async def _get_or_create_player(
    session: AsyncSession, discord_id: int, display_name: str
) -> Player:
    result = await session.execute(select(Player).where(Player.discord_id == discord_id))
    player = result.scalar_one_or_none()
    if player is None:
        player = Player(discord_id=discord_id, display_name=display_name)
        session.add(player)
        await session.flush()
    else:
        player.display_name = display_name
    return player


async def _apply_change(
    session: AsyncSession,
    *,
    discord_id: int,
    display_name: str,
    amount: int,
    tx_type: TxType,
    reason: str,
    officer_id: int | None,
    allow_negative: bool = False,
) -> DkpChangeResult:
    player = await _get_or_create_player(session, discord_id, display_name)

    new_balance = player.current_dkp + amount
    if new_balance < 0 and not allow_negative:
        raise InsufficientDKPError(need=-amount, have=player.current_dkp)

    player.current_dkp = new_balance
    if amount > 0:
        player.total_earned += amount
    else:
        player.total_spent += -amount

    tx = Transaction(
        player_id=player.id,
        amount=amount,
        balance_after=new_balance,
        type=tx_type.value,
        reason=reason,
        officer_id=officer_id,
    )
    session.add(tx)
    await session.flush()

    return DkpChangeResult(player=_player_to_dto(player), transaction=_tx_to_dto(tx))


async def add_dkp(
    discord_id: int, display_name: str, amount: int, reason: str, officer_id: int
) -> DkpChangeResult:
    async with session_maker() as session:
        async with session.begin():
            return await _apply_change(
                session,
                discord_id=discord_id,
                display_name=display_name,
                amount=amount,
                tx_type=TxType.EARN,
                reason=reason,
                officer_id=officer_id,
            )


async def spend_dkp(
    discord_id: int, display_name: str, amount: int, reason: str, officer_id: int
) -> DkpChangeResult:
    async with session_maker() as session:
        async with session.begin():
            return await _apply_change(
                session,
                discord_id=discord_id,
                display_name=display_name,
                amount=-amount,
                tx_type=TxType.SPEND,
                reason=reason,
                officer_id=officer_id,
            )


async def penalize(
    discord_id: int, display_name: str, amount: int, reason: str, officer_id: int
) -> DkpChangeResult:
    async with session_maker() as session:
        async with session.begin():
            return await _apply_change(
                session,
                discord_id=discord_id,
                display_name=display_name,
                amount=-amount,
                tx_type=TxType.PENALTY,
                reason=reason,
                officer_id=officer_id,
                allow_negative=True,
            )


async def decay_all(percent: int) -> DecayResult:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Player).where(Player.current_dkp > 0))
            players = result.scalars().all()

            total_removed = 0
            affected = 0
            for p in players:
                loss = (p.current_dkp * percent) // 100
                if loss <= 0:
                    continue
                p.current_dkp -= loss
                p.total_spent += loss
                total_removed += loss
                affected += 1
                tx = Transaction(
                    player_id=p.id,
                    amount=-loss,
                    balance_after=p.current_dkp,
                    type=TxType.DECAY.value,
                    reason=f"Еженедельное списание {percent}%",
                    officer_id=None,
                )
                session.add(tx)

            return DecayResult(affected_players=affected, total_removed=total_removed)


async def apply_auction_deduct(
    session: AsyncSession,
    discord_id: int,
    display_name: str,
    amount: int,
    item_name: str,
) -> DkpChangeResult:
    """Внутренний метод — вызывается из auction_service внутри его транзакции."""
    return await _apply_change(
        session,
        discord_id=discord_id,
        display_name=display_name,
        amount=-amount,
        tx_type=TxType.AUCTION,
        reason=f"Аукцион: {item_name}",
        officer_id=None,
        allow_negative=False,
    )
