import discord
from discord import app_commands
from discord.ext import commands

from bot.config import settings
from bot.services import dkp_service
from bot.ui import embeds
from bot.utils import logger_channel
from bot.utils.checks import is_admin, is_officer


class OfficerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="добавить", description="Начислить DKP игроку")
    @app_commands.describe(
        игрок="Игрок, которому начисляем",
        количество="Количество DKP",
        причина="Причина начисления",
    )
    @is_officer()
    async def add(
        self,
        interaction: discord.Interaction,
        игрок: discord.Member,
        количество: app_commands.Range[int, 1],
        причина: str,
    ) -> None:
        await interaction.response.defer()
        result = await dkp_service.add_dkp(
            игрок.id, игрок.display_name, количество, причина, interaction.user.id
        )
        await interaction.followup.send(embed=embeds.dkp_change(result))
        await logger_channel.send_log(
            self.bot, embeds.log_dkp_change(result, interaction.user)
        )

    @app_commands.command(name="списать", description="Списать DKP у игрока")
    @app_commands.describe(
        игрок="Игрок, у которого списываем",
        количество="Количество DKP",
        причина="Причина списания",
    )
    @is_officer()
    async def spend(
        self,
        interaction: discord.Interaction,
        игрок: discord.Member,
        количество: app_commands.Range[int, 1],
        причина: str,
    ) -> None:
        await interaction.response.defer()
        result = await dkp_service.spend_dkp(
            игрок.id, игрок.display_name, количество, причина, interaction.user.id
        )
        await interaction.followup.send(embed=embeds.dkp_change(result))
        await logger_channel.send_log(
            self.bot, embeds.log_dkp_change(result, interaction.user)
        )

    @app_commands.command(name="штраф", description="Выписать штраф игроку (может уйти в минус)")
    @app_commands.describe(
        игрок="Игрок, которого штрафуем",
        количество="Размер штрафа",
        причина="Причина штрафа",
    )
    @is_officer()
    async def penalty(
        self,
        interaction: discord.Interaction,
        игрок: discord.Member,
        количество: app_commands.Range[int, 1],
        причина: str,
    ) -> None:
        await interaction.response.defer()
        result = await dkp_service.penalize(
            игрок.id, игрок.display_name, количество, причина, interaction.user.id
        )
        await interaction.followup.send(embed=embeds.dkp_change(result))
        await logger_channel.send_log(
            self.bot, embeds.log_dkp_change(result, interaction.user)
        )

    @app_commands.command(
        name="списание",
        description=f"Списать {settings.DKP_DECAY_PERCENT}% DKP у всех игроков (только администратор)",
    )
    @is_admin()
    async def decay(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        result = await dkp_service.decay_all(settings.DKP_DECAY_PERCENT)

        embed = embeds.decay_report(result, settings.DKP_DECAY_PERCENT, interaction.user)
        await interaction.followup.send(embed=embed)
        await logger_channel.send_log(self.bot, embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OfficerCog(bot))
