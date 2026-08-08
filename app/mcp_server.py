from mcp.server.fastmcp import FastMCP
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pinterest_client import search_public_pinterest, download_pinterest_pin, pinterest_query_slug
from app.youtube_client import search_youtube_videos, download_youtube_video, youtube_query_slug

mcp = FastMCP("pinterest-cli")

# --- Pinterest Tools ---

@mcp.tool()
async def pinterest_search(query: str, limit: int = 5) -> str:
    """Search public Pinterest for visual reference photos and images."""
    _, raw_pins = await search_public_pinterest(query=query, limit=limit)
    results = []
    for i, p in enumerate(raw_pins, start=1):
        w = p.width
        h = p.height
        ar = round(w / h, 4) if w and h else None
        results.append({
            "index": i,
            "pin_id": str(p.pin_id),
            "title": str(p.title),
            "description": str(p.description),
            "pinner": str(p.pinner or ""),
            "width": w,
            "height": h,
            "aspect_ratio": ar,
            "pin_url": str(p.pin_url),
            "image_url": str(p.image_url)
        })
    out = {"ok": True, "command": "search", "source": "pinterest", "query": query, "count": len(results), "results": results}
    return json.dumps(out, indent=2)

@mcp.tool()
async def pinterest_download(query: str, index: int = 1, output: str = ".") -> str:
    """Download a specific Pinterest pin by index to a local folder."""
    query_slug = pinterest_query_slug(query)
    _, raw_pins = await search_public_pinterest(query=query, limit=max(index, 10))
    if index < 1 or index > len(raw_pins):
        out = {"ok": False, "error": {"code": "INVALID_INDEX", "message": f"Index {index} out of range (1..{len(raw_pins)})"}}
    else:
        target = raw_pins[index - 1]
        out_dir = Path(output).resolve()
        stem = out_dir / f"{query_slug}-{index:02d}-{target.pin_id}"
        saved_path = await download_pinterest_pin(target, stem)
        w = target.width
        h = target.height
        ar = round(w / h, 4) if w and h else None
        res = {
            "index": index,
            "pin_id": str(target.pin_id),
            "title": str(target.title),
            "description": str(target.description),
            "pinner": str(target.pinner or ""),
            "width": w,
            "height": h,
            "aspect_ratio": ar,
            "pin_url": str(target.pin_url),
            "image_url": str(target.image_url),
            "local_path": str(saved_path)
        }
        out = {"ok": True, "command": "download", "source": "pinterest", "query": query, "result": res}
    return json.dumps(out, indent=2)

@mcp.tool()
async def pinterest_fetch(query: str, limit: int = 3, output: str = ".") -> str:
    """Search and batch download top Pinterest photos directly to disk."""
    query_slug = pinterest_query_slug(query)
    _, raw_pins = await search_public_pinterest(query=query, limit=limit)
    out_dir = Path(output).resolve()
    downloaded = []
    for i, p in enumerate(raw_pins, start=1):
        try:
            stem = out_dir / f"{query_slug}-{i:02d}-{p.pin_id}"
            sp = await download_pinterest_pin(p, stem)
            w = p.width
            h = p.height
            ar = round(w / h, 4) if w and h else None
            downloaded.append({
                "index": i,
                "pin_id": str(p.pin_id),
                "title": str(p.title),
                "pin_url": str(p.pin_url),
                "image_url": str(p.image_url),
                "local_path": str(sp)
            })
        except Exception:
            pass
    out = {"ok": True, "command": "fetch", "source": "pinterest", "query": query, "count": len(downloaded), "downloaded": downloaded}
    return json.dumps(out, indent=2)

# --- YouTube Tools ---

@mcp.tool()
async def youtube_search(query: str, limit: int = 5) -> str:
    """Search YouTube for videos matching a topic or title query."""
    videos = await search_youtube_videos(query=query, limit=limit)
    results = []
    for i, v in enumerate(videos, start=1):
        results.append({
            "index": i,
            "video_id": str(v.video_id),
            "title": str(v.title),
            "duration_str": str(v.duration_str),
            "uploader": str(v.uploader),
            "view_count": v.view_count,
            "video_url": str(v.video_url),
            "thumbnail_url": str(v.thumbnail_url)
        })
    out = {"ok": True, "command": "search", "source": "youtube", "query": query, "count": len(results), "results": results}
    return json.dumps(out, indent=2)

@mcp.tool()
async def youtube_download(query: str, index: int = 1, output: str = ".", format: str = "mp4", quality: int = 720) -> str:
    """Download a specific YouTube video by index to local folder."""
    query_slug = youtube_query_slug(query)
    videos = await search_youtube_videos(query=query, limit=max(index, 5))
    if index < 1 or index > len(videos):
        out = {"ok": False, "error": {"code": "INVALID_INDEX", "message": f"Index {index} out of range (1..{len(videos)})"}}
    else:
        target = videos[index - 1]
        out_dir = Path(output).resolve()
        filename_stem = f"{query_slug}-{index:02d}-{target.video_id}"
        saved_path = await download_youtube_video(
            video_url=target.video_url,
            output_dir=out_dir,
            filename_stem=filename_stem,
            format_type=format,
            max_height=quality
        )
        res = {
            "index": index,
            "video_id": str(target.video_id),
            "title": str(target.title),
            "duration_str": str(target.duration_str),
            "uploader": str(target.uploader),
            "video_url": str(target.video_url),
            "local_path": str(saved_path)
        }
        out = {"ok": True, "command": "download", "source": "youtube", "query": query, "result": res}
    return json.dumps(out, indent=2)

@mcp.tool()
async def youtube_fetch(query: str, limit: int = 2, output: str = ".", format: str = "mp4", quality: int = 720) -> str:
    """Search and batch download top YouTube videos to disk."""
    query_slug = youtube_query_slug(query)
    videos = await search_youtube_videos(query=query, limit=limit)
    out_dir = Path(output).resolve()
    downloaded = []
    for i, v in enumerate(videos, start=1):
        try:
            filename_stem = f"{query_slug}-{i:02d}-{v.video_id}"
            sp = await download_youtube_video(
                video_url=v.video_url,
                output_dir=out_dir,
                filename_stem=filename_stem,
                format_type=format,
                max_height=quality
            )
            downloaded.append({
                "index": i,
                "video_id": str(v.video_id),
                "title": str(v.title),
                "video_url": str(v.video_url),
                "local_path": str(sp)
            })
        except Exception:
            pass
    out = {"ok": True, "command": "fetch", "source": "youtube", "query": query, "count": len(downloaded), "downloaded": downloaded}
    return json.dumps(out, indent=2)

if __name__ == "__main__":
    mcp.run()
