import asyncio
from services.bot_service import MusicBot
from config import get_config
import discord

config = get_config()


async def main() -> None:
    bot = MusicBot()
    async with bot:
        await bot.start(config.discord_bot_key)


if __name__ == "__main__":
    asyncio.run(main())
