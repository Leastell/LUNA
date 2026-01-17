import ctypes.util
import os
import discord
from config import get_config

config = get_config()

#  ----- Generators -----


def generate_embed(title, description="") -> discord.Embed:
    return discord.Embed(title=title, description=description, color=config.embed_color)


def generate_track_embed(audio_info, queue: bool = False) -> discord.Embed:
    """Build the now playing embed from audio info."""
    cleaned_title = audio_info["title"].split("(")[0].strip()
    embed = generate_embed(
        title=f"🎵 Now Playing",
        description=f"[{cleaned_title}]({audio_info["webpage_url"]})",
    )
    if queue:
        embed.title = "➡️ Queued Track"
    if audio_info.get("thumbnail"):
        embed.set_thumbnail(url=audio_info["thumbnail"])
    if audio_info.get("addedBy") and not queue:
        embed.add_field(
            name="Requested by",
            value=f"<@{audio_info["addedBy"].id}>",
            inline=False,
        )
    if audio_info.get("duration"):
        duration_seconds = int(audio_info["duration"])
        minutes, seconds = divmod(duration_seconds, 60)
        formatted_duration = f"{minutes}:{seconds:02d}"
        embed.add_field(name="Duration", value=formatted_duration, inline=True)
    return embed


async def start_playback(
    self,
    voice_client: discord.VoiceClient,
    audio_info,
    interaction: discord.Interaction | None = None,
) -> None:
    self.voice_client = voice_client

    source = discord.FFmpegPCMAudio(
        audio_info["stream_url"],
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        options="-vn",
    )

    embed = self.build_now_playing_embed(audio_info)
    if interaction:
        self.status_message = await interaction.followup.send(embed=embed)
    elif self.status_channel:
        self.status_message = await self.status_channel.send(embed=embed)

    self.is_playing = True
    voice_client.play(source, after=self.post_playback_handler)


# ----- Require -----


async def require_guild(interaction: discord.Interaction) -> discord.Guild | None:
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True,
        )
        return None

    return interaction.guild


async def require_member(interaction: discord.Interaction) -> discord.Member | None:
    guild = await require_guild(interaction)
    if guild is None:
        return

    user = interaction.user
    if not isinstance(user, discord.Member):
        await interaction.response.send_message(
            "Could not determine member information.",
            ephemeral=True,
        )
        return None

    return user


async def require_member_voice_channel(
    interaction: discord.Interaction,
) -> discord.VoiceChannel | None:
    member = await require_member(interaction)
    if member is None:
        return None

    voice_state = member.voice
    if voice_state is None or voice_state.channel is None:
        return None

    if isinstance(voice_state.channel, discord.StageChannel):
        return None

    # voice_state.channel can be VoiceChannel or StageChannel; we filtered StageChannel
    return voice_state.channel


async def require_voice_client(
    interaction: discord.Interaction,
) -> discord.VoiceClient | None:
    guild = await require_guild(interaction)
    if guild is None:
        return None

    vc = guild.voice_client
    if not isinstance(vc, discord.VoiceClient):
        return None

    return vc

    # if not bot_voice_client:
    #     embed = generate_embed(
    #     title="❌ Not in voice channel",
    #     description="Join a voice channel and use `/summon` to summon the bot.",
    # )
    # await interaction.followup.send(embed=embed)


# ----- Checkers ----


def ensure_opus_loaded() -> None:
    if discord.opus.is_loaded():
        return

    candidates: list[str] = []

    # 1) Best effort: ask the system loader
    found = ctypes.util.find_library("opus")
    if found:
        candidates.append(found)  # may be a name, not a full path

    # 2) Common macOS locations (Intel + Apple Silicon + MacPorts)
    candidates += [
        "/opt/homebrew/lib/libopus.dylib",
        "/usr/local/lib/libopus.dylib",
        "/opt/local/lib/libopus.dylib",
        "/usr/lib/libopus.dylib",  # sometimes exists, often not
    ]

    # 3) If Homebrew is present, ask it where opus lives (NO installing)
    # Only used to locate the already-installed library.
    try:
        import subprocess

        brew_prefix = subprocess.check_output(
            ["brew", "--prefix", "opus"], text=True
        ).strip()
        candidates.append(os.path.join(brew_prefix, "lib", "libopus.dylib"))
    except Exception:
        pass

    last_error: Exception | None = None

    for cand in candidates:
        if not cand:
            continue

        # If it's a full path, require it exists
        if os.path.isabs(cand) and not os.path.exists(cand):
            continue

        try:
            # Sanity check: can the dynamic loader open it?
            ctypes.CDLL(cand)
            discord.opus.load_opus(cand)
            if discord.opus.is_loaded():
                print(f"✅ Opus loaded: {cand}")
                return
        except Exception as e:
            last_error = e

    raise RuntimeError(
        "Could not load Opus (libopus). Tried:\n  - "
        + "\n  - ".join(candidates)
        + (f"\nLast error: {last_error}" if last_error else "")
    )
