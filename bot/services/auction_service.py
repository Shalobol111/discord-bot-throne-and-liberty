import asyncio
from datetime import datetime, timezone

from sqlalchemy import asc, func, select

from bot.database.engine import session_maker
from bot.database.models import Auction, AuctionStatus, Bid, LootHistory, Player
from bot.services.dkp_service import apply_auction_deduct
from bot.services.dtos import AuctionDTO, AuctionResult, PlayerDTO
from bot.services.exceptions import (
    AuctionAlreadyActiveError,
    InsufficientDKPError,
    InvalidBidError,
    NoActiveAuctionError,
)

# Один лок на всё — гильдийный бот работает на одном сервере
_auction_lock = asyncio.Lock()


def _player_to_dto(p: Player) -> PlayerDTO:
    return PlayerDTO(
        discord_id=p.discord_id,
        display_name=p.display_name,
        current_dkp=p.current_dkp,
        total_earned=p.total_earned,
        total_spent=p.total_spent,
    )


async def _build_auction_dto(session, auction: Auction) -> AuctionDTO:
    # Получаем топ-ставку
    top_result = await session.execute(
        select(Bid, Player)
        .join(Player, Bid.player_id == Player.id)
        .where(Bid.auction_id == auction.id)
        .order_by(Bid.amount.desc(), asc(Bid.created_at))
        .limit(1)
    )
    top_row = top_result.first()

    count_result = await session.execute(
        select(func.count()).select_from(Bid).where(Bid.auction_id == auction.id)
    )
    total_bids = count_result.scalar_one()

    top_bid = None
    top_bidder_name = None
    top_bidder_discord_id = None
    if top_row:
        bid, player = top_row
        top_bid = bid.amount
        top_bidder_name = player.display_name
        top_bidder_discord_id = player.discord_id

    return AuctionDTO(
        id=auction.id,
        item_name=auction.item_name,
        min_bid=auction.min_bid,
        bid_step=auction.bid_step,
        image_url=auction.image_url,
        status=auction.status,
        top_bid=top_bid,
        top_bidder_name=top_bidder_name,
        top_bidder_discord_id=top_bidder_discord_id,
        total_bids=total_bids,
    )


async def get_active_auction() -> AuctionDTO | None:
    async with session_maker() as session:
        result = await session.execute(
            select(Auction).where(Auction.status == AuctionStatus.ACTIVE.value)
        )
        auction = result.scalar_one_or_none()
        if auction is None:
            return None
        return await _build_auction_dto(session, auction)


async def start_auction(
    item_name: str,
    min_bid: int,
    bid_step: int,
    image_url: str | None,
    channel_id: int,
    started_by: int,
) -> AuctionDTO:
    async with _auction_lock:
        async with session_maker() as session:
            async with session.begin():
                existing = await session.execute(
                    select(Auction).where(Auction.status == AuctionStatus.ACTIVE.value)
                )
                active = existing.scalar_one_or_none()
                if active is not None:
                    raise AuctionAlreadyActiveError(active.item_name)

                auction = Auction(
                    item_name=item_name,
                    min_bid=min_bid,
                    bid_step=bid_step,
                    image_url=image_url,
                    status=AuctionStatus.ACTIVE.value,
                    channel_id=channel_id,
                    started_by=started_by,
                )
                session.add(auction)
                await session.flush()

                return AuctionDTO(
                    id=auction.id,
                    item_name=auction.item_name,
                    min_bid=auction.min_bid,
                    bid_step=auction.bid_step,
                    image_url=auction.image_url,
                    status=auction.status,
                    top_bid=None,
                    top_bidder_name=None,
                    top_bidder_discord_id=None,
                    total_bids=0,
                )


async def place_bid(discord_id: int, display_name: str, amount: int) -> AuctionDTO:
    async with _auction_lock:
        async with session_maker() as session:
            async with session.begin():
                a_result = await session.execute(
                    select(Auction).where(Auction.status == AuctionStatus.ACTIVE.value)
                )
                auction = a_result.scalar_one_or_none()
                if auction is None:
                    raise NoActiveAuctionError()

                # Текущая максимальная ставка
                top_result = await session.execute(
                    select(func.max(Bid.amount)).where(Bid.auction_id == auction.id)
                )
                current_top = top_result.scalar_one_or_none() or 0

                min_valid = max(auction.min_bid, current_top + auction.bid_step)
                if amount < auction.min_bid:
                    raise InvalidBidError(
                        f"Ставка {amount} ниже минимальной ({auction.min_bid} DKP)"
                    )
                if amount < min_valid:
                    raise InvalidBidError(
                        f"Ставка должна быть минимум {min_valid} DKP "
                        f"(текущий топ {current_top} + шаг {auction.bid_step})"
                    )
                if (amount - auction.min_bid) % auction.bid_step != 0:
                    raise InvalidBidError(
                        f"Ставка должна быть кратна шагу {auction.bid_step} DKP "
                        f"(от минимальной {auction.min_bid})"
                    )

                # Получаем или создаём игрока
                p_result = await session.execute(
                    select(Player).where(Player.discord_id == discord_id)
                )
                player = p_result.scalar_one_or_none()
                if player is None:
                    player = Player(discord_id=discord_id, display_name=display_name)
                    session.add(player)
                    await session.flush()
                else:
                    player.display_name = display_name

                if player.current_dkp < amount:
                    raise InsufficientDKPError(need=amount, have=player.current_dkp)

                # Если игрок уже ставил в этом аукционе — обновляем ставку
                existing_bid_result = await session.execute(
                    select(Bid).where(
                        Bid.auction_id == auction.id,
                        Bid.player_id == player.id,
                    )
                )
                existing_bid = existing_bid_result.scalar_one_or_none()

                if existing_bid:
                    existing_bid.amount = amount
                    existing_bid.created_at = datetime.now(timezone.utc)
                else:
                    bid = Bid(
                        auction_id=auction.id,
                        player_id=player.id,
                        amount=amount,
                    )
                    session.add(bid)

                await session.flush()
                return await _build_auction_dto(session, auction)


async def finish_auction(officer_id: int) -> AuctionResult:
    async with _auction_lock:
        async with session_maker() as session:
            async with session.begin():
                a_result = await session.execute(
                    select(Auction).where(Auction.status == AuctionStatus.ACTIVE.value)
                )
                auction = a_result.scalar_one_or_none()
                if auction is None:
                    raise NoActiveAuctionError()

                # Топ-ставка: макс. сумма, при равенстве — самая ранняя
                top_result = await session.execute(
                    select(Bid, Player)
                    .join(Player, Bid.player_id == Player.id)
                    .where(Bid.auction_id == auction.id)
                    .order_by(Bid.amount.desc(), asc(Bid.created_at))
                    .limit(1)
                )
                top_row = top_result.first()

                now = datetime.now(timezone.utc)

                if top_row is None:
                    # Ставок не было — отмена
                    auction.status = AuctionStatus.CANCELLED.value
                    auction.finished_at = now
                    dto = await _build_auction_dto(session, auction)
                    return AuctionResult(auction=dto, winner=None, winning_bid=None)

                top_bid, winner_player = top_row
                winning_amount = top_bid.amount

                # Повторная проверка баланса победителя внутри транзакции
                if winner_player.current_dkp < winning_amount:
                    raise InsufficientDKPError(
                        need=winning_amount, have=winner_player.current_dkp
                    )

                # Списание DKP у победителя
                deduct_result = await apply_auction_deduct(
                    session,
                    discord_id=winner_player.discord_id,
                    display_name=winner_player.display_name,
                    amount=winning_amount,
                    item_name=auction.item_name,
                )

                # Запись в лут
                loot = LootHistory(
                    auction_id=auction.id,
                    player_id=winner_player.id,
                    item_name=auction.item_name,
                    cost=winning_amount,
                )
                session.add(loot)

                auction.status = AuctionStatus.FINISHED.value
                auction.winner_id = winner_player.id
                auction.winning_bid = winning_amount
                auction.finished_at = now
                await session.flush()

                winner_dto = _player_to_dto(deduct_result.player)
                dto = await _build_auction_dto(session, auction)
                return AuctionResult(auction=dto, winner=winner_dto, winning_bid=winning_amount)
