import discord
from discord import app_commands
from discord.ext import commands

from bot.services import history_service
from bot.ui import embeds


class LootCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="лут", description="История выигранных предметов на аукционах")
    @app_commands.describe(количество="Количество записей (по умолчанию 10)")
    async def loot(
        self,
        interaction: discord.Interaction,
        количество: app_commands.Range[int, 1, 50] = 10,
    ) -> None:
        await interaction.response.defer()
        items = await history_service.get_loot(количество)
        await interaction.followup.send(embed=embeds.loot_list(items))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LootCog(bot))
