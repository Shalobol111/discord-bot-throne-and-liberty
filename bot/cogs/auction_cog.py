import discord
from discord import app_commands
from discord.ext import commands

from bot.services import auction_service
from bot.ui import embeds
from bot.utils import logger_channel
from bot.utils.checks import is_officer


class AuctionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="аукционначать", description="Начать аукцион на предмет")
    @app_commands.describe(
        название="Название предмета",
        мин_ставка="Минимальная ставка в DKP",
        шаг_ставки="Шаг ставки в DKP",
        изображение="URL изображения предмета (необязательно)",
    )
    @is_officer()
    async def auction_start(
        self,
        interaction: discord.Interaction,
        название: str,
        мин_ставка: app_commands.Range[int, 1],
        шаг_ставки: app_commands.Range[int, 1],
        изображение: str | None = None,
    ) -> None:
        await interaction.response.defer()
        auction = await auction_service.start_auction(
            item_name=название,
            min_bid=мин_ставка,
            bid_step=шаг_ставки,
            image_url=изображение,
            channel_id=interaction.channel_id,
            started_by=interaction.user.id,
        )
        embed = embeds.auction_active(auction)
        msg = await interaction.followup.send(embed=embed, wait=True)

        # Логируем старт
        log_embed = discord.Embed(
            title=f"🔨 Аукцион запущен: {auction.item_name}",
            color=0xF1C40F,
        )
        log_embed.add_field(name="Мин. ставка", value=f"{auction.min_bid} DKP", inline=True)
        log_embed.add_field(name="Шаг", value=f"{auction.bid_step} DKP", inline=True)
        log_embed.set_footer(text=f"Запустил: {interaction.user.display_name}")
        log_embed.timestamp = discord.utils.utcnow()
        await logger_channel.send_log(self.bot, log_embed)

    @app_commands.command(name="ставка", description="Сделать ставку на текущем аукционе")
    @app_commands.describe(сумма="Ваша ставка в DKP")
    async def bid(
        self,
        interaction: discord.Interaction,
        сумма: app_commands.Range[int, 1],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        auction = await auction_service.place_bid(
            discord_id=interaction.user.id,
            display_name=interaction.user.display_name,
            amount=сумма,
        )
        await interaction.followup.send(
            embed=embeds.auction_bid_placed(auction, interaction.user.display_name),
            ephemeral=True,
        )
        # Публичное обновление — сообщаем в канал
        await interaction.channel.send(
            embed=embeds.auction_active(auction)
        )

    @app_commands.command(name="аукционзавершить", description="Завершить текущий аукцион")
    @is_officer()
    async def auction_finish(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        result = await auction_service.finish_auction(officer_id=interaction.user.id)

        embed = embeds.auction_finished(result)
        await interaction.followup.send(embed=embed)
        await logger_channel.send_log(
            self.bot, embeds.log_auction_finished(result, interaction.user)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AuctionCog(bot))
