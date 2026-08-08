from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import asyncio
import re
import json
import yt_dlp

@dataclass
class YouTubeVideo:
    video_id: str
    title: str
    duration: Optional[int]
    duration_str: str
    uploader: str
    view_count: Optional[int]
    video_url: str
    thumbnail_url: str

def youtube_query_slug(query: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", query.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:40] or "youtube-video"

def _format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "N/A"
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

async def search_youtube_videos(query: str, limit: int = 5) -> list[YouTubeVideo]:
    clean_query = " ".join(query.split()).strip()
    if not clean_query:
        raise ValueError("Search query cannot be empty")
    limit = max(1, min(int(limit), 20))

    ydl_opts = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb", "android", "web"],
            }
        },
    }

    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch{limit}:{clean_query}", download=False)
            entries = res.get("entries", []) if res else []
            videos = []
            for entry in entries:
                if not entry:
                    continue
                vid = entry.get("id", "")
                title = entry.get("title", "") or "Untitled Video"
                duration = entry.get("duration")
                uploader = entry.get("uploader", "") or entry.get("channel", "") or "Unknown"
                view_count = entry.get("view_count")
                url = f"https://www.youtube.com/watch?v={vid}" if vid else entry.get("url", "")
                thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""
                videos.append(YouTubeVideo(
                    video_id=vid,
                    title=title,
                    duration=duration,
                    duration_str=_format_duration(duration),
                    uploader=uploader,
                    view_count=view_count,
                    video_url=url,
                    thumbnail_url=thumb
                ))
            return videos

    return await asyncio.to_thread(_search)

async def download_youtube_video(
    video_url: str,
    output_dir: Path,
    filename_stem: str,
    format_type: str = "mp4",
    max_height: int = 720
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(output_dir / f"{filename_stem}.%(ext)s")

    if format_type.lower() == "mp3":
        format_spec = "bestaudio/best"
        postprocessors = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        format_spec = f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_height}][ext=mp4]/best"
        postprocessors = []

    ydl_opts = {
        "format": format_spec,
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": postprocessors,
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb", "android", "web"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            saved_filename = ydl.prepare_filename(info)
            if format_type.lower() == "mp3":
                saved_filename = str(Path(saved_filename).with_suffix(".mp3"))
            return Path(saved_filename)

    return await asyncio.to_thread(_download)
