import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import settings
from bot.database import Base, engine
from bot.services.exceptions import (
    AuctionAlreadyActiveError,
    DKPBotError,
    InsufficientDKPError,
    InvalidBidError,
    NoActiveAuctionError,
)
from bot.ui import embeds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

COGS = [
    "bot.cogs.player_cog",
    "bot.cogs.officer_cog",
    "bot.cogs.auction_cog",
    "bot.cogs.loot_cog",
    "bot.cogs.export_cog",
]


class DKPBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        # Создаём таблицы если их нет (для запуска без alembic)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Загружаем коги
        for cog in COGS:
            await self.load_extension(cog)
            logger.info("Загружен ког: %s", cog)

        # Синхронизируем slash-команды на конкретный сервер (мгновенно)
        guild = discord.Object(id=settings.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info("Синхронизировано %d команд на сервер %d", len(synced), settings.GUILD_ID)

    async def on_ready(self) -> None:
        logger.info("Бот запущен как %s (ID: %d)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="за DKP гильдии 👑",
            )
        )


def _error_to_message(error: Exception) -> str:
    if isinstance(error, InsufficientDKPError):
        return f"Недостаточно DKP: нужно **{error.need}**, есть **{error.have}**."
    if isinstance(error, AuctionAlreadyActiveError):
        return f"Уже идёт аукцион: **{error.item_name}**. Сначала завершите его."
    if isinstance(error, NoActiveAuctionError):
        return "Нет активного аукциона."
    if isinstance(error, InvalidBidError):
        return error.reason
    if isinstance(error, DKPBotError):
        return str(error)
    if isinstance(error, app_commands.CheckFailure):
        return str(error)
    return f"Произошла непредвиденная ошибка: {error}"


async def main() -> None:
    bot = DKPBot()

    @bot.tree.error
    async def on_app_command_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        # Разворачиваем CommandInvokeError
        cause = error.__cause__ if error.__cause__ is not None else error
        message = _error_to_message(cause)

        embed = embeds.error(message)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            pass

        # Логируем неожиданные ошибки
        if not isinstance(cause, (DKPBotError, app_commands.CheckFailure)):
            logger.exception("Необработанная ошибка в команде /%s", interaction.command)

    async with bot:
        await bot.start(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
