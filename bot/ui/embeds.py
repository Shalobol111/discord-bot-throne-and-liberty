from datetime import timezone

import discord

from bot.database.models import TxType
from bot.services.dtos import (
    AuctionDTO,
    AuctionResult,
    DecayResult,
    DkpChangeResult,
    LootDTO,
    PlayerDTO,
    TransactionDTO,
)
from bot.ui import colors

# ──────────────────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────────────────

_TX_EMOJI = {
    TxType.EARN: "🟢",
    TxType.SPEND: "🔴",
    TxType.PENALTY: "🔴",
    TxType.AUCTION: "🟡",
    TxType.DECAY: "⚫",
}

_TX_LABEL = {
    TxType.EARN: "Начисление",
    TxType.SPEND: "Списание",
    TxType.PENALTY: "Штраф",
    TxType.AUCTION: "Аукцион",
    TxType.DECAY: "Снижение",
}


def _sign(amount: int) -> str:
    return f"+{amount}" if amount > 0 else str(amount)


def _fmt_tx(tx: TransactionDTO) -> str:
    emoji = _TX_EMOJI.get(tx.type, "⚪")
    label = _TX_LABEL.get(tx.type, tx.type.value)
    ts = int(tx.created_at.replace(tzinfo=timezone.utc).timestamp())
    return (
        f"{emoji} **{_sign(tx.amount)} DKP** — {label}\n"
        f"└ {tx.reason} • <t:{ts}:R>"
    )


# ──────────────────────────────────────────────────────────
# Команды игрока
# ──────────────────────────────────────────────────────────

def dkp_overview(player: PlayerDTO, txs: list[TransactionDTO]) -> discord.Embed:
    embed = discord.Embed(
        title=f"📊 DKP — {player.display_name}",
        color=colors.BLUE,
    )
    embed.add_field(name="💰 Текущий баланс", value=f"**{player.current_dkp}** DKP", inline=True)
    embed.add_field(name="📈 Всего заработано", value=f"{player.total_earned} DKP", inline=True)
    embed.add_field(name="📉 Всего потрачено", value=f"{player.total_spent} DKP", inline=True)

    if txs:
        history_text = "\n".join(_fmt_tx(t) for t in txs)
        embed.add_field(name="📋 Последние операции", value=history_text, inline=False)
    else:
        embed.add_field(name="📋 История", value="Операций пока нет.", inline=False)

    return embed


def top_list(players: list[PlayerDTO]) -> discord.Embed:
    embed = discord.Embed(title="🏆 Топ игроков по DKP", color=colors.GOLD)
    if not players:
        embed.description = "Список пуст."
        return embed

    lines = []
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, p in enumerate(players, 1):
        medal = medals.get(i, f"**{i}.**")
        lines.append(f"{medal} {p.display_name} — **{p.current_dkp} DKP**")

    embed.description = "\n".join(lines)
    return embed


def history_list(display_name: str, txs: list[TransactionDTO]) -> discord.Embed:
    embed = discord.Embed(
        title=f"📋 История DKP — {display_name}",
        color=colors.BLUE,
    )
    if not txs:
        embed.description = "Операций пока нет."
    else:
        embed.description = "\n\n".join(_fmt_tx(t) for t in txs)
    return embed


# ──────────────────────────────────────────────────────────
# Операции офицеров (для игрока и лога)
# ──────────────────────────────────────────────────────────

def dkp_change(result: DkpChangeResult) -> discord.Embed:
    tx = result.transaction
    p = result.player

    if tx.type == TxType.EARN:
        color = colors.GREEN
        title = "🟢 DKP начислено"
    elif tx.type == TxType.PENALTY:
        color = colors.RED
        title = "🔴 Штраф выписан"
    elif tx.type == TxType.SPEND:
        color = colors.RED
        title = "🔴 DKP списано"
    else:
        color = colors.GREY
        title = "⚫ Изменение DKP"

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="Игрок", value=p.display_name, inline=True)
    embed.add_field(name="Изменение", value=f"**{_sign(tx.amount)} DKP**", inline=True)
    embed.add_field(name="Баланс", value=f"{tx.balance_after} DKP", inline=True)
    embed.add_field(name="Причина", value=tx.reason, inline=False)
    return embed


def log_dkp_change(result: DkpChangeResult, officer: discord.Member) -> discord.Embed:
    embed = dkp_change(result)
    embed.set_footer(text=f"Офицер: {officer.display_name}")
    ts = int(result.transaction.created_at.replace(tzinfo=timezone.utc).timestamp())
    embed.timestamp = result.transaction.created_at.replace(tzinfo=timezone.utc)
    return embed


def decay_report(result: DecayResult, percent: int, officer: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title=f"⚫ Списание {percent}% DKP",
        color=colors.GREY,
    )
    embed.add_field(name="Затронуто игроков", value=str(result.affected_players), inline=True)
    embed.add_field(name="Всего списано", value=f"{result.total_removed} DKP", inline=True)
    embed.set_footer(text=f"Инициатор: {officer.display_name}")
    embed.timestamp = discord.utils.utcnow()
    return embed


# ──────────────────────────────────────────────────────────
# Аукцион
# ──────────────────────────────────────────────────────────

def auction_active(a: AuctionDTO) -> discord.Embed:
    embed = discord.Embed(title=f"🔨 Аукцион: {a.item_name}", color=colors.GOLD)
    embed.add_field(name="Мин. ставка", value=f"{a.min_bid} DKP", inline=True)
    embed.add_field(name="Шаг", value=f"{a.bid_step} DKP", inline=True)
    embed.add_field(name="Ставок", value=str(a.total_bids), inline=True)

    if a.top_bid is not None:
        embed.add_field(
            name="🥇 Лидер",
            value=f"{a.top_bidder_name} — **{a.top_bid} DKP**",
            inline=False,
        )
    else:
        embed.add_field(name="🥇 Лидер", value="Ставок пока нет", inline=False)

    if a.image_url:
        embed.set_image(url=a.image_url)

    embed.set_footer(text="Используйте /ставка <сумма> для участия")
    return embed


def auction_bid_placed(a: AuctionDTO, bidder: str) -> discord.Embed:
    embed = discord.Embed(
        title="🟡 Ставка принята",
        description=f"**{bidder}** ставит **{a.top_bid} DKP** на «{a.item_name}»",
        color=colors.GOLD,
    )
    embed.add_field(name="Всего ставок", value=str(a.total_bids), inline=True)
    next_min = (a.top_bid or a.min_bid) + a.bid_step
    embed.add_field(name="Мин. следующая", value=f"{next_min} DKP", inline=True)
    return embed


def auction_finished(result: AuctionResult) -> discord.Embed:
    if result.winner is None:
        embed = discord.Embed(
            title="❌ Аукцион завершён без ставок",
            description=f"Лот «{result.auction.item_name}» не нашёл покупателя.",
            color=colors.GREY,
        )
        return embed

    embed = discord.Embed(
        title="🏆 Аукцион завершён!",
        color=colors.GOLD,
    )
    embed.add_field(name="Лот", value=result.auction.item_name, inline=False)
    embed.add_field(name="Победитель", value=result.winner.display_name, inline=True)
    embed.add_field(name="Финальная ставка", value=f"**{result.winning_bid} DKP**", inline=True)
    embed.add_field(
        name="Остаток DKP",
        value=f"{result.winner.current_dkp} DKP",
        inline=True,
    )
    return embed


def log_auction_finished(result: AuctionResult, officer: discord.Member) -> discord.Embed:
    embed = auction_finished(result)
    embed.set_footer(text=f"Завершил: {officer.display_name}")
    embed.timestamp = discord.utils.utcnow()
    return embed


# ──────────────────────────────────────────────────────────
# Лут
# ──────────────────────────────────────────────────────────

def loot_list(items: list[LootDTO]) -> discord.Embed:
    embed = discord.Embed(title="📦 История лута", color=colors.GOLD)
    if not items:
        embed.description = "Пока никто ничего не выиграл."
        return embed

    lines = []
    for item in items:
        ts = int(item.created_at.replace(tzinfo=timezone.utc).timestamp())
        lines.append(
            f"🟡 **{item.item_name}** — {item.winner_name} за **{item.cost} DKP** • <t:{ts}:R>"
        )
    embed.description = "\n".join(lines)
    return embed


# ──────────────────────────────────────────────────────────
# Ошибки
# ──────────────────────────────────────────────────────────

def error(message: str) -> discord.Embed:
    return discord.Embed(title="❌ Ошибка", description=message, color=colors.RED)


def success(message: str) -> discord.Embed:
    return discord.Embed(description=f"✅ {message}", color=colors.GREEN)
