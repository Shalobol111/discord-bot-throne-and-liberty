from discord import app_commands

from bot.config import settings


def is_officer():
    """Проверяет, что у пользователя есть одна из офицерских ролей или права администратора."""
    async def predicate(interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        member_role_ids = {r.id for r in interaction.user.roles}
        if member_role_ids & set(settings.OFFICER_ROLE_IDS):
            return True
        raise app_commands.CheckFailure(
            "У вас нет прав для этой команды. Требуется роль офицера."
        )
    return app_commands.check(predicate)


def is_admin():
    """Только администраторы сервера."""
    async def predicate(interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        raise app_commands.CheckFailure(
            "У вас нет прав для этой команды. Требуются права администратора."
        )
    return app_commands.check(predicate)
