import discord
from discord import app_commands
from discord.ext import commands

from bot.services import export_service
from bot.services.export_service import TABLE_REGISTRY
from bot.ui import embeds
from bot.utils.checks import is_officer

# Варианты выбора: «Все таблицы» + по одной на каждую таблицу
_CHOICES = [app_commands.Choice(name="📚 Все таблицы", value="__all__")] + [
    app_commands.Choice(name=human, value=tech)
    for tech, (_model, human) in TABLE_REGISTRY.items()
]


class ExportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="экспорт",
        description="Выгрузить данные в Excel-файл (.xlsx)",
    )
    @app_commands.describe(таблица="Какую таблицу выгрузить (по умолчанию — все)")
    @app_commands.choices(таблица=_CHOICES)
    @is_officer()
    async def export(
        self,
        interaction: discord.Interaction,
        таблица: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if таблица is None or таблица.value == "__all__":
            table_names = None
            label = "все таблицы"
        else:
            table_names = [таблица.value]
            label = TABLE_REGISTRY[таблица.value][1]

        path = await export_service.export_to_excel(table_names)

        file = discord.File(str(path), filename=path.name)
        embed = embeds.success(f"Готов экспорт: **{label}**")
        embed.set_footer(text="Откройте файл в Excel / LibreOffice / Google Таблицах")

        await interaction.followup.send(embed=embed, file=file, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ExportCog(bot))
