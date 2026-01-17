import asyncio
from typing import Any, Mapping, Optional

import yt_dlp
from config import get_config


class YouTubeService:
    def __init__(self) -> None:
        config = get_config()

        ydl_options: dict[str, Any] = {
            # Prefer non-HLS so ffmpeg doesn't fetch m3u8 segments
            "format": "bestaudio[protocol!=m3u8][protocol!=m3u8_native]/bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch",
            "socket_timeout": 30,
            # Enable EJS challenge solving
            "remote_components": ["ejs:github"],  # recommended
            # IMPORTANT: python API expects dict, not list
            "js_runtimes": {"deno": {}},
            # basic headers (yt-dlp will add more per-video in result["http_headers"])
            "http_headers": {"User-Agent": "Mozilla/5.0"},
        }

        if getattr(config, "ytdl_cookies", None):
            ydl_options["cookiefile"] = config.ytdl_cookies
            print(f"✓ Successfully loaded cookies file: {config.ytdl_cookies}")

        self.ydl = yt_dlp.YoutubeDL(ydl_options)  # type: ignore

    async def search(self, query: str) -> Optional[Mapping[str, Any]]:
        result = await asyncio.to_thread(self.ydl.extract_info, query, download=False)
        if not result:
            return None

        if "entries" in result:
            entries = result.get("entries") or []
            if not entries:
                return None
            result = entries[0]

        return {
            "title": result.get("title"),
            "webpage_url": result.get("webpage_url"),
            "duration": result.get("duration"),
            "stream_url": result.get("url"),
            "thumbnail": result.get("thumbnail"),
            "http_headers": result.get("http_headers") or {},
        }
