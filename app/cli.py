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

    # Fetch enough pins to fulfill the requested index
    search_limit = max(args.index, 8)
    search_limit = min(search_limit, 50)

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
        if errors:
            print(f"\nEncountered {len(errors)} download errors:")
            for err in errors:
                print(f"[{err['index']}] Pin {err['pin_id']}: {err['error']}")


def create_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        prog="clipsearch",
        description="ClipSearch CLI - Search public Pinterest pins and download high-resolution images.",
    )
    subparsers = parser.add_subparsers(dest="service", help="Service to interact with")

    pinterest_parser = subparsers.add_parser(
        "pinterest",
        help="Search public Pinterest pins and download images.",
        description="Search public Pinterest pins and download Pinterest-hosted images.",
    )
    pinterest_subparsers = pinterest_parser.add_subparsers(dest="command", help="Pinterest action")

    # Search command
    search_parser = pinterest_subparsers.add_parser(
        "search",
        help="Search public Pinterest pins by query string.",
        description="Search public Pinterest pins by query string and return metadata.",
    )
    search_parser.add_argument("query", type=str, help="Search query string")
    search_parser.add_argument("--limit", type=int, default=8, help="Maximum number of results to return (1-50, default: 8)")
    search_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON to stdout")
    search_parser.add_argument("--pretty", action="store_true", help="Format JSON output with indentation")

    # Download command
    download_parser = pinterest_subparsers.add_parser(
        "download",
        help="Download a specific image result from Pinterest search by index.",
        description="Download a specific image result from public Pinterest search using 1-based index.",
    )
    download_parser.add_argument("--query", type=str, required=True, help="Search query string")
    download_parser.add_argument("--index", type=int, required=True, help="1-based index of result to download")
    download_parser.add_argument("--output", type=str, default="./downloads/pinterest", help="Destination folder for downloaded images (default: ./downloads/pinterest)")
    download_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON to stdout")
    download_parser.add_argument("--pretty", action="store_true", help="Format JSON output with indentation")

    # Fetch command
    fetch_parser = pinterest_subparsers.add_parser(
        "fetch",
        help="Search and download a batch of images from Pinterest.",
        description="Search public Pinterest pins and download all returned images into output directory.",
    )
    fetch_parser.add_argument("query", type=str, help="Search query string")
    fetch_parser.add_argument("--limit", type=int, default=8, help="Number of images to fetch (1-50, default: 8)")
    fetch_parser.add_argument("--output", type=str, default="./downloads/pinterest", help="Destination folder for downloaded images (default: ./downloads/pinterest)")
    fetch_parser.add_argument("--json", action="store_true", help="Output results strictly as JSON to stdout")
    fetch_parser.add_argument("--pretty", action="store_true", help="Format JSON output with indentation")

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    if not args.service:
        parser.print_help()
        sys.exit(0)

    if args.service == "pinterest":
        if not args.command:
            # Print pinterest subcommands help
            sys.argv.append("--help")
            parser.parse_args()
            sys.exit(0)

        if args.command == "search":
            asyncio.run(_run_search(args))
        elif args.command == "download":
            asyncio.run(_run_download(args))
        elif args.command == "fetch":
            asyncio.run(_run_fetch(args))


if __name__ == "__main__":
    main()
