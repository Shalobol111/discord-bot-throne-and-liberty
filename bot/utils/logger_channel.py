import logging

import discord

from bot.config import settings

logger = logging.getLogger(__name__)


async def send_log(bot: discord.Client, embed: discord.Embed) -> None:
    channel = bot.get_channel(settings.DKP_LOG_CHANNEL_ID)
    if channel is None:
        logger.warning("Лог-канал %s не найден", settings.DKP_LOG_CHANNEL_ID)
        return
    try:
        await channel.send(embed=embed)
    except discord.HTTPException as e:
        logger.error("Не удалось отправить лог в канал: %s", e)
