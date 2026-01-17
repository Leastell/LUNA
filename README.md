# LUNA

A Discord bot for audio playback from youtube

## Commands

-   `/summon` - Summon the bot to your voice channel
-   `/play <query>` - Search YouTube and play audio
-   `/queue <query>` - Add audio to the queue
-   `/skip` - Skip the currently playing track
-   `/leave` - Leave the voice channel

## Requirements

-   Python 3.10+
-   discord.py
-   yt-dlp
-   ffmpeg

## Installation

1. Clone the repository
2. Install system dependencies:

    **macOS:**

    ```bash
    brew install ffmpeg libopus
    ```

    **Ubuntu/Debian:**

    ```bash
    sudo apt-get install ffmpeg libopus-dev
    ```

    **Windows:**

    - Download FFmpeg from https://ffmpeg.org/download.html
    - Download libopus from https://opus-codec.org/downloads/

3. Install Python dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Create a `config.py` file with your Discord bot token:

    ```python
    def get_config():
        return Config(
            discord_bot_key="YOUR_BOT_TOKEN",
            debug_guild_id=None  # Optional: Set to guild ID for debug mode
        )
    ```

5. Run the bot:
    ```bash
    python main.py
    ```

## Optional Configuration

### YouTube Cookie Authentication

If you need to authenticate with YouTube, you can provide a cookies file:

1. Export your YouTube cookies using a browser extension like [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndcbcohstpfkmjlbijfeebclabs)
2. Save the cookies file (e.g., `cookies.txt`)
3. Set the environment variable before running the bot:
    ```bash
    export YTDL_COOKIES=/path/to/cookies.txt
    python main.py
    ```

The bot will automatically use the cookies file for YouTube requests if the path is valid.

## Project Structure

```
├── main.py              # Entry point
├── config.py            # Configuration (gitignored)
├── requirements.txt     # Python dependencies
├── cogs/
│   ├── audio.py        # Audio cog with playback logic
│   ├── helpers.py      # Helper functions
│   └── __init__.py
└── services/
    ├── bot_service.py   # Bot service
    ├── youtube_service.py  # YouTube search service
    └── __init__.py
```

## License

MIT
