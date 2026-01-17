import asyncio
from collections import deque
from typing import cast
import discord
from discord import StageChannel, app_commands, VoiceChannel
from discord.ext import commands
from config import get_config
from services.bot_service import MusicBot
from services.youtube_service import YouTubeService
from .helpers import (
    generate_embed,
    require_voice_client,
    require_member_voice_channel,
    ensure_opus_loaded,
    generate_track_embed,
)

config = get_config()


class Audio(commands.Cog):
    def __init__(self, bot: MusicBot) -> None:
        ensure_opus_loaded()
        self.bot = bot
        self.yt_service = YouTubeService()
        self.audio_queue: deque = deque()

        self.status_channel: discord.TextChannel | None = None
        self.status_message: discord.Message | None = None
        self.voice_client: discord.VoiceClient | None = None
        self.is_playing: bool = False
        self.leave_timeout_task: asyncio.Task | None = None

    async def run_yt_search(self, query: str, interaction: discord.Interaction):
        result = await self.yt_service.search(query)
        if result is None:
            embed = generate_embed(
                title="😵‍💫 No results found",
                description="No results found for your query, try pasting the youtube link.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return None
        return result

    def post_playback_handler(self, error: Exception | None) -> None:
        if error:
            print(f"Playback error: {error!r}")

        # Schedule async handling safely
        loop = self.bot.loop
        loop.call_soon_threadsafe(lambda: asyncio.create_task(self.play_next_track()))

    async def play_next_track(self) -> None:
        # If there's something in the queue, play it
        if len(self.audio_queue) > 0:
            up_next: dict = self.audio_queue.popleft()
            bot_vc = self.voice_client
            if bot_vc is None or not bot_vc.is_connected():
                # TODO: Handle this
                return
            await self.start_playback(bot_vc, up_next)
        else:
            self.is_playing = False

    async def start_playback(
        self,
        voice_client: discord.VoiceClient,
        audio_info,
        interaction: discord.Interaction | None = None,
    ) -> None:
        self.voice_client = voice_client

        # Prepare headers for FFmpeg
        headers = audio_info.get("http_headers") or {}
        headers.setdefault("User-Agent", "Mozilla/5.0")
        header_lines = "".join(f"{k}: {v}\r\n" for k, v in headers.items())

        before_options = (
            "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
            f'-headers "{header_lines}"'
        )

        source = discord.FFmpegPCMAudio(
            audio_info["stream_url"],
            before_options=before_options,
            options="-vn",
        )

        embed = generate_track_embed(audio_info)
        if interaction:
            self.status_message = await interaction.followup.send(embed=embed)
        elif self.status_channel:
            self.status_message = await self.status_channel.send(embed=embed)

        self.is_playing = True
        voice_client.play(source, after=self.post_playback_handler)

    @app_commands.command(
        name="summon", description="Summon the bot to your voice channel"
    )
    async def summon(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        user_voice_channel = await require_member_voice_channel(interaction)
        if user_voice_channel is None:
            embed = generate_embed(
                title="❌ You are not in a voice channel",
                description="You must be connected to a voice channel to use this command.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        bot_vc = await require_voice_client(interaction)

        # If bot is already connected, move if needed
        if bot_vc is not None:
            if bot_vc.channel == user_voice_channel:
                embed = generate_embed(
                    title="✅ I'm already in your voice channel.",
                    description="Use `/play` to begin playing audio.",
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            await bot_vc.move_to(user_voice_channel)
            embed = generate_embed(
                title=f"🔄 Moved to **{user_voice_channel.name}**",
                description="Use `/play` to begin playing audio.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Otherwise connect
        self.voice_client = await user_voice_channel.connect()
        if isinstance(interaction.channel, discord.TextChannel):
            self.status_channel = interaction.channel
        embed = generate_embed(
            title=f"🔊 Joined **{user_voice_channel.name}**",
            description="Use `/play` to begin playing audio.",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="queue", description="Add audio to the queue")
    @app_commands.describe(
        query="The title or Youtube URL of the audio you wish to queue",
    )
    async def queue(
        self,
        interaction: discord.Interaction,
        query: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        bot_vc = await require_voice_client(interaction)
        if bot_vc is None:
            embed = generate_embed(
                title="❌ Not in voice channel",
                description="Join a voice channel and use `/summon` to summon the bot.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Search for the audio
        result = await self.run_yt_search(query, interaction)
        if result is None:
            return

        self.audio_queue.append({**result, "addedBy": interaction.user})

        embed = generate_track_embed(
            {**result, "addedBy": interaction.user}, queue=True
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="play", description="Play audio")
    @app_commands.describe(
        query="The title or Youtube URL of the audio you wish to play",
    )
    async def play(
        self,
        interaction: discord.Interaction,
        query: str,
    ) -> None:
        await interaction.response.defer()

        bot_vc = await require_voice_client(interaction)
        if bot_vc is None:
            embed = generate_embed(
                title="❌ Not in voice channel",
                description="Join a voice channel and use `/summon` to summon the bot.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Search for the audio
        result = await self.run_yt_search(query, interaction)
        if result is None:
            return

        print(result)

        if isinstance(interaction.channel, discord.TextChannel):
            self.status_channel = interaction.channel
        await self.start_playback(
            bot_vc, {**result, "addedBy": interaction.user}, interaction=interaction
        )

    @app_commands.command(name="skip", description="Skip whatever is currently playing")
    async def skip(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer()
        if not self.is_playing or not self.voice_client:
            embed = generate_embed(
                title="❌ Nothing is playing",
                description="Use `/play` to begin playing audio.",
            )
            await interaction.followup.send(embed=embed)
            return

        embed = generate_embed(title=f"⏭️ Track skipped")
        await interaction.followup.send(embed=embed)

        self.voice_client.stop()
        await self.play_next_track()

    async def disconnect_from_voice(self) -> None:
        """Disconnect from voice channel and clean up state."""
        if self.voice_client is None or not self.voice_client.is_connected():
            return

        # Stop audio playback gracefully before disconnecting
        if self.voice_client.is_playing():
            self.voice_client.stop()
        await self.voice_client.disconnect()

        # Clean up state
        self.voice_client = None
        self.is_playing = False
        self.audio_queue.clear()
        self.status_message = None
        self.leave_timeout_task = None

    @app_commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if self.voice_client is None or not self.voice_client.is_connected():
            embed = generate_embed(
                title="❌ Not in voice channel",
                description="The bot is not currently in a voice channel.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        channel_name = self.voice_client.channel.name
        await self.disconnect_from_voice()
        embed = generate_embed(
            title=f"💨 Left **{channel_name}**",
            description="Join a voice channel and use `/summon` to summon the bot.",
        )
        await interaction.followup.send(embed=embed)

    async def check_if_alone(self) -> None:
        """Check if bot is alone in voice channel and leave after 30 seconds."""
        if self.voice_client is None or not self.voice_client.is_connected():
            return

        # Check if bot is the only one in the channel
        members_in_channel = [m for m in self.voice_client.channel.members if not m.bot]

        if len(members_in_channel) == 0:
            # No one is in the channel, schedule leaving after 30 seconds
            await asyncio.sleep(30)
            if self.voice_client and self.voice_client.is_connected():
                # Double-check no one has joined in the meantime
                members_in_channel = [
                    m for m in self.voice_client.channel.members if not m.bot
                ]
                if len(members_in_channel) == 0:
                    await self.disconnect_from_voice()
                    # Send inactivity message
                    if self.status_channel:
                        embed = generate_embed(
                            title="💨 Left due to inactivity",
                            description="Join a voice channel and use `/summon` to summon the bot.",
                        )
                        await self.status_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle voice state updates and auto-leave if bot is alone."""
        if (
            member.bot
            or self.voice_client is None
            or not self.voice_client.is_connected()
        ):
            return

        if (
            before.channel == self.voice_client.channel
            and after.channel != self.voice_client.channel
        ):
            # Check if bot is now alone
            members_in_channel = [
                m for m in self.voice_client.channel.members if not m.bot
            ]

            if len(members_in_channel) == 0:
                # Cancel existing timeout task if any
                if self.leave_timeout_task and not self.leave_timeout_task.done():
                    self.leave_timeout_task.cancel()

                # Start new timeout task only if vc is empty
                self.leave_timeout_task = asyncio.create_task(self.check_if_alone())

        # Check if someone joined the bot's channel
        elif (
            before.channel != self.voice_client.channel
            and after.channel == self.voice_client.channel
        ):
            # Cancel the leave timeout if someone rejoins
            if self.leave_timeout_task and not self.leave_timeout_task.done():
                self.leave_timeout_task.cancel()
                self.leave_timeout_task = None


async def setup(bot: MusicBot) -> None:
    await bot.add_cog(Audio(bot))

    if config.debug_guild_id:
        guild = discord.Object(id=config.debug_guild_id)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
