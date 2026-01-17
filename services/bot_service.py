import discord
import logging
from discord.ext import commands

from config import get_config

config = get_config()

logging.basicConfig(level=logging.INFO)


class MusicBot(commands.Bot):
    inVoice: bool = False

    def __init__(
        self,
    ):
        commands.Bot.__init__(
            self, command_prefix=config.command_prefix, intents=config.intents
        )

    async def setup_hook(self) -> None:
        for ext in config.enabled_cogs:
            await self.load_extension(f"cogs.{ext}")
            print("registered " + ext)

        # await self.tree.sync()

    async def on_ready(self) -> None:
        # Fires when the bot is ready
        logging.info(f"Logged in as {self.user}")
