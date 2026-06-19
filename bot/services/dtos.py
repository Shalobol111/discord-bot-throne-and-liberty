from dataclasses import dataclass
from datetime import datetime

from bot.database.models import TxType


@dataclass(slots=True)
class PlayerDTO:
    discord_id: int
    display_name: str
    current_dkp: int
    total_earned: int
    total_spent: int


@dataclass(slots=True)
class TransactionDTO:
    id: int
    amount: int
    balance_after: int
    type: TxType
    reason: str
    officer_id: int | None
    created_at: datetime


@dataclass(slots=True)
class DkpChangeResult:
    player: PlayerDTO
    transaction: TransactionDTO


@dataclass(slots=True)
class DecayResult:
    affected_players: int
    total_removed: int


@dataclass(slots=True)
class AuctionDTO:
    id: int
    item_name: str
    min_bid: int
    bid_step: int
    image_url: str | None
    status: str
    top_bid: int | None
    top_bidder_name: str | None
    top_bidder_discord_id: int | None
    total_bids: int


@dataclass(slots=True)
class AuctionResult:
    auction: AuctionDTO
    winner: PlayerDTO | None
    winning_bid: int | None


@dataclass(slots=True)
class LootDTO:
    item_name: str
    winner_name: str
    winner_discord_id: int
    cost: int
    created_at: datetime
