from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)

# expire_on_commit=False — критично для async: атрибуты не протухают после commit()
session_maker = async_sessionmaker(engine, expire_on_commit=False)
