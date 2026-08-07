from mcp.server.fastmcp import FastMCP
import json
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pinterest_client import search_public_pinterest, download_pinterest_pin

mcp = FastMCP("pinterest-cli")

@mcp.tool()
async def pinterest_search(query: str, limit: int = 5) -> str:
    """Search public Pinterest for visual reference photos and images."""
    raw_pins = await asyncio.to_thread(search_public_pinterest, query, limit)
    results = []
    for i, p in enumerate(raw_pins, start=1):
        w = p.get("width")
        h = p.get("height")
        ar = round(w / h, 4) if w and h else None
        results.append({
            "index": i,
            "pin_id": str(p.get("id", "")),
            "title": str(p.get("title", "") or p.get("grid_title", "")),
            "description": str(p.get("description", "")),
            "pinner": str(p.get("pinner", {}).get("username", "") if isinstance(p.get("pinner"), dict) else ""),
            "width": w,
            "height": h,
            "aspect_ratio": ar,
            "pin_url": f"https://www.pinterest.com/pin/{p.get('id')}/" if p.get("id") else "",
            "image_url": str(p.get("image_url", ""))
        })
    out = {"ok": True, "command": "search", "source": "pinterest", "query": query, "count": len(results), "results": results}
    return json.dumps(out, indent=2)

@mcp.tool()
async def pinterest_download(query: str, index: int = 1, output: str = ".") -> str:
    """Download a specific Pinterest pin by index to a local folder."""
    raw_pins = await asyncio.to_thread(search_public_pinterest, query, max(index, 10))
    if index < 1 or index > len(raw_pins):
        out = {"ok": False, "error": {"code": "INVALID_INDEX", "message": f"Index {index} out of range (1..{len(raw_pins)})"}}
    else:
        target = raw_pins[index - 1]
        saved_path = await asyncio.to_thread(download_pinterest_pin, target, output, query, index)
        w = target.get("width")
        h = target.get("height")
        ar = round(w / h, 4) if w and h else None
        res = {
            "index": index,
            "pin_id": str(target.get("id", "")),
            "title": str(target.get("title", "") or target.get("grid_title", "")),
            "description": str(target.get("description", "")),
            "pinner": str(target.get("pinner", {}).get("username", "") if isinstance(target.get("pinner"), dict) else ""),
            "width": w,
            "height": h,
            "aspect_ratio": ar,
            "pin_url": f"https://www.pinterest.com/pin/{target.get('id')}/" if target.get("id") else "",
            "image_url": str(target.get("image_url", "")),
            "local_path": saved_path
        }
        out = {"ok": True, "command": "download", "source": "pinterest", "query": query, "result": res}
    return json.dumps(out, indent=2)

@mcp.tool()
async def pinterest_fetch(query: str, limit: int = 3, output: str = ".") -> str:
    """Search and batch download top Pinterest photos directly to disk."""
    raw_pins = await asyncio.to_thread(search_public_pinterest, query, limit)
    downloaded = []
    for i, p in enumerate(raw_pins, start=1):
        try:
            sp = await asyncio.to_thread(download_pinterest_pin, p, output, query, i)
            w = p.get("width")
            h = p.get("height")
            ar = round(w / h, 4) if w and h else None
            downloaded.append({
                "index": i,
                "pin_id": str(p.get("id", "")),
                "title": str(p.get("title", "") or p.get("grid_title", "")),
                "pin_url": f"https://www.pinterest.com/pin/{p.get('id')}/" if p.get("id") else "",
                "image_url": str(p.get("image_url", "")),
                "local_path": sp
            })
        except Exception:
            pass
    out = {"ok": True, "command": "fetch", "source": "pinterest", "query": query, "count": len(downloaded), "downloaded": downloaded}
    return json.dumps(out, indent=2)

if __name__ == "__main__":
    mcp.run()
