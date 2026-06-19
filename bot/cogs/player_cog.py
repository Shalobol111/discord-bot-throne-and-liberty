import discord
from discord import app_commands
from discord.ext import commands

from bot.services import history_service
from bot.ui import embeds


class PlayerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="дкп", description="Показать ваш текущий DKP и последние операции")
    async def dkp(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        player, txs = await history_service.get_player_overview(
            interaction.user.id, interaction.user.display_name
        )
        if player is None:
            await interaction.followup.send(
                embed=embeds.error("У вас ещё нет DKP. Обратитесь к офицеру."),
                ephemeral=True,
            )
            return
        await interaction.followup.send(embed=embeds.dkp_overview(player, txs), ephemeral=True)

    @app_commands.command(name="топ", description="Топ игроков по DKP")
    @app_commands.describe(количество="Количество игроков в топе (по умолчанию 10)")
    async def top(
        self,
        interaction: discord.Interaction,
        количество: app_commands.Range[int, 1, 50] = 10,
    ) -> None:
        await interaction.response.defer()
        players = await history_service.get_top(количество)
        await interaction.followup.send(embed=embeds.top_list(players))

    @app_commands.command(name="история", description="Последние 10 операций DKP")
    @app_commands.describe(игрок="Игрок (если не указан — ваша история)")
    async def history(
        self,
        interaction: discord.Interaction,
        игрок: discord.Member | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        target = игрок or interaction.user
        display_name, txs = await history_service.get_history(target.id)
        if display_name is None:
            await interaction.followup.send(
                embed=embeds.error(f"У игрока **{target.display_name}** нет истории DKP."),
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            embed=embeds.history_list(display_name, txs), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlayerCog(bot))
