import discord
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    discord_bot_key: str = Field(..., alias="DISCORD_TOKEN")
    debug_guild_id: str = Field(..., alias="DEBUG_GUILD_ID")
    command_prefix: str = Field("%", alias="COMMAND_PREFIX")

    enabled_cogs: list[str] = Field(["audio"])
    embed_color: discord.Color = Field(
        default_factory=lambda: discord.Color.from_str("0xc896ff"), alias="EMBED_COLOR"
    )
    ytdl_cookies: str = Field("", alias="YTDL_COOKIES")

    @field_validator("embed_color", mode="before")
    @classmethod
    def validate_embed_color(cls, v):
        if v is None or v == "":
            return discord.Color.from_str("0xc896ff")
        if isinstance(v, str):
            return discord.Color.from_str(v)
        return v

    intents: discord.Intents = discord.Intents.default()
    model_config = SettingsConfigDict(env_file=".env")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.discord_bot_key:
            raise ValueError("DISCORD_TOKEN must be set in .env file")


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
