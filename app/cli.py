import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

import httpx

from app.pinterest_client import (
    PinterestPin,
    download_pinterest_pin,
    pinterest_query_slug,
    search_public_pinterest,
)
from app.youtube_client import (
    YouTubeVideo,
    download_youtube_video,
    search_youtube_videos,
    youtube_query_slug,
)


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        if "--json" in sys.argv:
            _handle_error(
                code="INVALID_ARGUMENT",
                message="Invalid CLI argument.",
                details=message,
                exit_code=2,
                is_json=True,
            )
        super().error(message)


def _pin_to_dict(pin: PinterestPin, index: int, local_path: str | None = None) -> dict[str, Any]:
    aspect_ratio = None
    if pin.width and pin.height and pin.height > 0:
        aspect_ratio = round(pin.width / pin.height, 4)
    return {
        "index": index,
        "pin_id": pin.pin_id,
        "title": pin.title,
        "description": pin.description,
        "pinner": pin.pinner,
        "width": pin.width,
        "height": pin.height,
        "aspect_ratio": aspect_ratio,
        "pin_url": pin.pin_url,
        "image_url": pin.image_url,
        "local_path": local_path,
    }


def _yt_to_dict(video: YouTubeVideo, index: int, local_path: str | None = None) -> dict[str, Any]:
    return {
        "index": index,
        "video_id": video.video_id,
        "title": video.title,
        "duration": video.duration,
        "duration_str": video.duration_str,
        "uploader": video.uploader,
        "view_count": video.view_count,
        "video_url": video.video_url,
        "thumbnail_url": video.thumbnail_url,
        "local_path": local_path,
    }


def _handle_error(
    code: str,
    message: str,
    details: str = "",
    exit_code: int = 1,
    is_json: bool = False,
    pretty: bool = False,
) -> NoReturn:
    if is_json:
        output = {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        }
        indent = 2 if pretty else None
        print(json.dumps(output, indent=indent), file=sys.stdout)
    else:
        detail_msg = f": {details}" if details else ""
        print(f"Error [{code}]: {message}{detail_msg}", file=sys.stderr)
    sys.exit(exit_code)


# --- Pinterest Handlers ---

async def _run_search(args: argparse.Namespace) -> None:
    query = args.query.strip()
    if not query:
        _handle_error("INVALID_ARGUMENT", "Query string cannot be empty.", exit_code=2, is_json=args.json, pretty=args.pretty)
    if args.limit < 1 or args.limit > 50:
        _handle_error("INVALID_ARGUMENT", "Limit must be between 1 and 50.", exit_code=2, is_json=args.json, pretty=args.pretty)

    try:
        search_url, pins = await search_public_pinterest(query, args.limit)
    except httpx.TransportError as exc:
        _handle_error("NETWORK_ERROR", "Network error occurred while reaching Pinterest.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)
    except Exception as exc:
        _handle_error("PINTEREST_SEARCH_FAILED", "Pinterest search failed.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)

    results = [_pin_to_dict(pin, idx + 1) for idx, pin in enumerate(pins)]
    
    if args.json:
        response = {
            "ok": True,
            "command": "search",
            "source": "pinterest",
            "query": query,
            "count": len(results),
            "results": results,
        }
        indent = 2 if args.pretty else None
        print(json.dumps(response, indent=indent), file=sys.stdout)
    else:
        print(f"Pinterest results for: {query}")
        if not results:
            print("No results found.")
            return
        for r in results:
            dims = f"{r['width']}x{r['height']}" if r['width'] and r['height'] else "unknown dims"
            title = r['title'] or r['description'] or "Untitled Pin"
            print(f"[{r['index']}] {title} ({dims}) - {r['pin_url']}")


async def _run_download(args: argparse.Namespace) -> None:
    query = args.query.strip()
    if not query:
        _handle_error("INVALID_ARGUMENT", "Query string cannot be empty.", exit_code=2, is_json=args.json, pretty=args.pretty)
    if args.index < 1:
        _handle_error("INVALID_ARGUMENT", "Index must be 1 or greater.", exit_code=2, is_json=args.json, pretty=args.pretty)

    search_limit = min(max(args.index, 8), 50)

    try:
        search_url, pins = await search_public_pinterest(query, search_limit)
    except httpx.TransportError as exc:
        _handle_error("NETWORK_ERROR", "Network error occurred while reaching Pinterest.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)
    except Exception as exc:
        _handle_error("PINTEREST_SEARCH_FAILED", "Pinterest search failed.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)

    if not pins:
        _handle_error("NO_RESULTS", "Pinterest search returned no results.", f"Query: {query}", exit_code=1, is_json=args.json, pretty=args.pretty)

    if args.index > len(pins):
        _handle_error(
            "INVALID_INDEX",
            f"Requested index {args.index} exceeds total results found ({len(pins)}).",
            f"Query yielded {len(pins)} pins.",
            exit_code=1,
            is_json=args.json,
            pretty=args.pretty,
        )

    selected_pin = pins[args.index - 1]
    query_slug = pinterest_query_slug(query)
    output_dir = Path(args.output)
    destination_stem = output_dir / f"{query_slug}-{args.index:02d}-{selected_pin.pin_id}"

    try:
        local_file = await download_pinterest_pin(selected_pin, destination_stem)
    except OSError as exc:
        _handle_error("FILESYSTEM_ERROR", "Failed to save downloaded image file.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)
    except httpx.TransportError as exc:
        _handle_error("NETWORK_ERROR", "Network error during image download.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)
    except Exception as exc:
        _handle_error("PINTEREST_DOWNLOAD_FAILED", "Failed to download Pinterest image.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)

    result_dict = _pin_to_dict(selected_pin, args.index, str(local_file))

    if args.json:
        response = {
            "ok": True,
            "command": "download",
            "source": "pinterest",
            "query": query,
            "result": result_dict,
        }
        indent = 2 if args.pretty else None
        print(json.dumps(response, indent=indent), file=sys.stdout)
    else:
        print(f"Downloaded pin [{args.index}] to {local_file}")
        print(f"Title: {selected_pin.title or selected_pin.description or 'Untitled'}")
        print(f"URL: {selected_pin.pin_url}")


async def _run_fetch(args: argparse.Namespace) -> None:
    query = args.query.strip()
    if not query:
        _handle_error("INVALID_ARGUMENT", "Query string cannot be empty.", exit_code=2, is_json=args.json, pretty=args.pretty)
    if args.limit < 1 or args.limit > 50:
        _handle_error("INVALID_ARGUMENT", "Limit must be between 1 and 50.", exit_code=2, is_json=args.json, pretty=args.pretty)

    try:
        search_url, pins = await search_public_pinterest(query, args.limit)
    except httpx.TransportError as exc:
        _handle_error("NETWORK_ERROR", "Network error occurred while reaching Pinterest.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)
    except Exception as exc:
        _handle_error("PINTEREST_SEARCH_FAILED", "Pinterest search failed.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)

    query_slug = pinterest_query_slug(query)
    output_dir = Path(args.output)

    successful_results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, pin in enumerate(pins, start=1):
        destination_stem = output_dir / f"{query_slug}-{idx:02d}-{pin.pin_id}"
        try:
            local_file = await download_pinterest_pin(pin, destination_stem)
            successful_results.append(_pin_to_dict(pin, idx, str(local_file)))
        except Exception as exc:
            errors.append({
                "index": idx,
                "pin_id": pin.pin_id,
                "error": str(exc),
            })

    if args.json:
        response = {
            "ok": True,
            "command": "fetch",
            "source": "pinterest",
            "query": query,
            "requested": args.limit,
            "downloaded": len(successful_results),
            "results": successful_results,
            "errors": errors,
        }
        indent = 2 if args.pretty else None
        print(json.dumps(response, indent=indent), file=sys.stdout)
    else:
        print(f"Downloaded {len(successful_results)}/{len(pins)} images for \"{query}\" to {output_dir}")
        for r in successful_results:
            title = r['title'] or r['description'] or "Untitled Pin"
            print(f"[{r['index']}] {title} -> {r['local_path']}")


# --- YouTube Handlers ---

async def _run_youtube_search(args: argparse.Namespace) -> None:
    query = args.query.strip()
    if not query:
        _handle_error("INVALID_ARGUMENT", "Query string cannot be empty.", exit_code=2, is_json=args.json, pretty=args.pretty)
    if args.limit < 1 or args.limit > 20:
        _handle_error("INVALID_ARGUMENT", "Limit must be between 1 and 20.", exit_code=2, is_json=args.json, pretty=args.pretty)

    try:
        videos = await search_youtube_videos(query, args.limit)
    except Exception as exc:
        _handle_error("YOUTUBE_SEARCH_FAILED", "YouTube search failed.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)

    results = [_yt_to_dict(v, idx + 1) for idx, v in enumerate(videos)]
    
    if args.json:
        response = {
            "ok": True,
            "command": "search",
            "source": "youtube",
            "query": query,
            "count": len(results),
            "results": results,
        }
        indent = 2 if args.pretty else None
        print(json.dumps(response, indent=indent), file=sys.stdout)
    else:
        print(f"YouTube results for: {query}")
        if not results:
            print("No results found.")
            return
        for r in results:
            print(f"[{r['index']}] {r['title']} ({r['duration_str']}) - {r['uploader']} - {r['video_url']}")


async def _run_youtube_download(args: argparse.Namespace) -> None:
    query = args.query.strip()
    if not query:
        _handle_error("INVALID_ARGUMENT", "Query string cannot be empty.", exit_code=2, is_json=args.json, pretty=args.pretty)
    if args.index < 1:
        _handle_error("INVALID_ARGUMENT", "Index must be 1 or greater.", exit_code=2, is_json=args.json, pretty=args.pretty)

    search_limit = max(args.index, 5)

    try:
        videos = await search_youtube_videos(query, search_limit)
    except Exception as exc:
        _handle_error("YOUTUBE_SEARCH_FAILED", "YouTube search failed.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)

    if not videos:
        _handle_error("NO_RESULTS", "YouTube search returned no results.", f"Query: {query}", exit_code=1, is_json=args.json, pretty=args.pretty)

    if args.index > len(videos):
        _handle_error(
            "INVALID_INDEX",
            f"Requested index {args.index} exceeds total results found ({len(videos)}).",
            f"Query yielded {len(videos)} videos.",
            exit_code=1,
            is_json=args.json,
            pretty=args.pretty,
        )

    selected_video = videos[args.index - 1]
    query_slug = youtube_query_slug(query)
    output_dir = Path(args.output)
    filename_stem = f"{query_slug}-{args.index:02d}-{selected_video.video_id}"

    try:
        local_file = await download_youtube_video(
            video_url=selected_video.video_url,
            output_dir=output_dir,
            filename_stem=filename_stem,
            format_type=getattr(args, "format", "mp4"),
            max_height=getattr(args, "quality", 720),
        )
    except Exception as exc:
        _handle_error("YOUTUBE_DOWNLOAD_FAILED", "Failed to download YouTube video.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)

    result_dict = _yt_to_dict(selected_video, args.index, str(local_file))

    if args.json:
        response = {
            "ok": True,
            "command": "download",
            "source": "youtube",
            "query": query,
            "result": result_dict,
        }
        indent = 2 if args.pretty else None
        print(json.dumps(response, indent=indent), file=sys.stdout)
    else:
        print(f"Downloaded YouTube video [{args.index}] to {local_file}")
        print(f"Title: {selected_video.title}")
        print(f"URL: {selected_video.video_url}")


async def _run_youtube_fetch(args: argparse.Namespace) -> None:
    query = args.query.strip()
    if not query:
        _handle_error("INVALID_ARGUMENT", "Query string cannot be empty.", exit_code=2, is_json=args.json, pretty=args.pretty)
    if args.limit < 1 or args.limit > 20:
        _handle_error("INVALID_ARGUMENT", "Limit must be between 1 and 20.", exit_code=2, is_json=args.json, pretty=args.pretty)

    try:
        videos = await search_youtube_videos(query, args.limit)
    except Exception as exc:
        _handle_error("YOUTUBE_SEARCH_FAILED", "YouTube search failed.", str(exc), exit_code=1, is_json=args.json, pretty=args.pretty)

    query_slug = youtube_query_slug(query)
    output_dir = Path(args.output)

    successful_results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, video in enumerate(videos, start=1):
        filename_stem = f"{query_slug}-{idx:02d}-{video.video_id}"
        try:
            local_file = await download_youtube_video(
                video_url=video.video_url,
                output_dir=output_dir,
                filename_stem=filename_stem,
                format_type=getattr(args, "format", "mp4"),
                max_height=getattr(args, "quality", 720),
            )
            successful_results.append(_yt_to_dict(video, idx, str(local_file)))
        except Exception as exc:
            errors.append({
                "index": idx,
                "video_id": video.video_id,
                "error": str(exc),
            })

    if args.json:
        response = {
            "ok": True,
            "command": "fetch",
            "source": "youtube",
            "query": query,
            "requested": args.limit,
            "downloaded": len(successful_results),
            "results": successful_results,
            "errors": errors,
        }
        indent = 2 if args.pretty else None
        print(json.dumps(response, indent=indent), file=sys.stdout)
    else:
        print(f"Downloaded {len(successful_results)}/{len(videos)} videos for \"{query}\" to {output_dir}")
        for r in successful_results:
            print(f"[{r['index']}] {r['title']} -> {r['local_path']}")


def create_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        prog="clipsearch",
        description="ClipSearch CLI - Search and download media from Pinterest and YouTube.",
    )
    subparsers = parser.add_subparsers(dest="service", help="Service to interact with (pinterest or youtube)")

    # --- Pinterest Parser ---
    pinterest_parser = subparsers.add_parser(
        "pinterest",
        help="Search public Pinterest pins and download images.",
        description="Search public Pinterest pins and download Pinterest-hosted images.",
    )
    pinterest_subparsers = pinterest_parser.add_subparsers(dest="command", help="Pinterest action")

    search_parser = pinterest_subparsers.add_parser("search", help="Search public Pinterest pins.")
    search_parser.add_argument("query", type=str, help="Search query string")
    search_parser.add_argument("--limit", type=int, default=8, help="Maximum results (1-50, default: 8)")
    search_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON")
    search_parser.add_argument("--pretty", action="store_true", help="Format JSON output")

    download_parser = pinterest_subparsers.add_parser("download", help="Download specific Pinterest pin by index.")
    download_parser.add_argument("--query", type=str, required=True, help="Search query string")
    download_parser.add_argument("--index", type=int, required=True, help="1-based index")
    download_parser.add_argument("--output", type=str, default="./downloads/pinterest", help="Destination folder")
    download_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON")
    download_parser.add_argument("--pretty", action="store_true", help="Format JSON output")

    fetch_parser = pinterest_subparsers.add_parser("fetch", help="Batch fetch Pinterest images.")
    fetch_parser.add_argument("query", type=str, help="Search query string")
    fetch_parser.add_argument("--limit", type=int, default=8, help="Number of images")
    fetch_parser.add_argument("--output", type=str, default="./downloads/pinterest", help="Destination folder")
    fetch_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON")
    fetch_parser.add_argument("--pretty", action="store_true", help="Format JSON output")

    # --- YouTube Parser ---
    youtube_parser = subparsers.add_parser(
        "youtube",
        help="Search YouTube videos and download video/audio files.",
        description="Search YouTube videos and download video/audio files using yt-dlp.",
    )
    youtube_subparsers = youtube_parser.add_subparsers(dest="command", help="YouTube action")

    yt_search_parser = youtube_subparsers.add_parser("search", help="Search YouTube videos.")
    yt_search_parser.add_argument("query", type=str, help="Search query string")
    yt_search_parser.add_argument("--limit", type=int, default=5, help="Maximum results (1-20, default: 5)")
    yt_search_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON")
    yt_search_parser.add_argument("--pretty", action="store_true", help="Format JSON output")

    yt_download_parser = youtube_subparsers.add_parser("download", help="Download specific YouTube video by index.")
    yt_download_parser.add_argument("--query", type=str, required=True, help="Search query string")
    yt_download_parser.add_argument("--index", type=int, required=True, help="1-based index")
    yt_download_parser.add_argument("--output", type=str, default="./downloads/youtube", help="Destination folder")
    yt_download_parser.add_argument("--format", type=str, choices=["mp4", "mp3"], default="mp4", help="Format: mp4 or mp3 (default: mp4)")
    yt_download_parser.add_argument("--quality", type=int, default=720, help="Max video height e.g. 720, 1080 (default: 720)")
    yt_download_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON")
    yt_download_parser.add_argument("--pretty", action="store_true", help="Format JSON output")

    yt_fetch_parser = youtube_subparsers.add_parser("fetch", help="Batch fetch YouTube videos.")
    yt_fetch_parser.add_argument("query", type=str, help="Search query string")
    yt_fetch_parser.add_argument("--limit", type=int, default=3, help="Number of videos to download (1-20, default: 3)")
    yt_fetch_parser.add_argument("--output", type=str, default="./downloads/youtube", help="Destination folder")
    yt_fetch_parser.add_argument("--format", type=str, choices=["mp4", "mp3"], default="mp4", help="Format: mp4 or mp3 (default: mp4)")
    yt_fetch_parser.add_argument("--quality", type=int, default=720, help="Max video height e.g. 720, 1080 (default: 720)")
    yt_fetch_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON")
    yt_fetch_parser.add_argument("--pretty", action="store_true", help="Format JSON output")

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    if not args.service:
        parser.print_help()
        sys.exit(0)

    if args.service == "pinterest":
        if not args.command:
            sys.argv.append("--help")
            parser.parse_args()
            sys.exit(0)

        if args.command == "search":
            asyncio.run(_run_search(args))
        elif args.command == "download":
            asyncio.run(_run_download(args))
        elif args.command == "fetch":
            asyncio.run(_run_fetch(args))

    elif args.service == "youtube":
        if not args.command:
            sys.argv.append("--help")
            parser.parse_args()
            sys.exit(0)

        if args.command == "search":
            asyncio.run(_run_youtube_search(args))
        elif args.command == "download":
            asyncio.run(_run_youtube_download(args))
        elif args.command == "fetch":
            asyncio.run(_run_youtube_fetch(args))


if __name__ == "__main__":
    main()
