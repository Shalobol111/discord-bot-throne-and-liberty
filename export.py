"""Быстрый экспорт данных в Excel без запуска бота.

Примеры запуска (из корня проекта):
    py export.py                      # все таблицы в один файл
    py export.py players              # только игроки
    py export.py players transactions # игроки + операции
    py export.py --list               # показать доступные таблицы
"""
import asyncio
import sys

from bot.services.export_service import TABLE_REGISTRY, export_to_excel


async def _run(table_names: list[str] | None) -> None:
    path = await export_to_excel(table_names)
    print(f"\nГотово! Файл сохранён:\n  {path.resolve()}\n")


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] in ("--list", "-l"):
        print("Доступные таблицы:")
        for tech, (_model, human) in TABLE_REGISTRY.items():
            print(f"  {tech:<15} — {human}")
        return

    if args and args[0] in ("--help", "-h"):
        print(__doc__)
        return

    table_names = args or None
    if table_names:
        unknown = [t for t in table_names if t not in TABLE_REGISTRY]
        if unknown:
            print(f"Неизвестные таблицы: {', '.join(unknown)}")
            print("Запустите 'py export.py --list' чтобы увидеть доступные.")
            sys.exit(1)

    asyncio.run(_run(table_names))


if __name__ == "__main__":
    main()
