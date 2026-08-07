import sys
import json
from app.pinterest_client import search_public_pinterest, download_pinterest_pin

def send_response(response):
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()

def handle_request(req):
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "pinterest-cli", "version": "0.1.0"}
            }
        })
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "pinterest_search",
                        "description": "Search public Pinterest for visual reference photos and images.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for Pinterest pins"},
                                "limit": {"type": "integer", "description": "Number of pins to fetch (default 5)", "default": 5}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "pinterest_download",
                        "description": "Download a specific Pinterest pin by index to a local folder.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for Pinterest pins"},
                                "index": {"type": "integer", "description": "1-based index of the pin from search results"},
                                "output": {"type": "string", "description": "Output directory path", "default": "."}
                            },
                            "required": ["query", "index"]
                        }
                    },
                    {
                        "name": "pinterest_fetch",
                        "description": "Search and batch download top Pinterest photos directly to disk.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query for Pinterest pins"},
                                "limit": {"type": "integer", "description": "Number of photos to download", "default": 3},
                                "output": {"type": "string", "description": "Output directory path", "default": "."}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        })
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        query = arguments.get("query", "")

        if tool_name == "pinterest_search":
            limit = int(arguments.get("limit", 5))
            raw_pins = search_public_pinterest(query=query, limit=limit)
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
            send_response({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]}})

        elif tool_name == "pinterest_download":
            idx = int(arguments.get("index", 1))
            output_dir = arguments.get("output", ".")
            raw_pins = search_public_pinterest(query=query, limit=max(idx, 10))
            if idx < 1 or idx > len(raw_pins):
                out = {"ok": False, "error": {"code": "INVALID_INDEX", "message": f"Index {idx} out of range (1..{len(raw_pins)})"}}
            else:
                target = raw_pins[idx - 1]
                saved_path = download_pinterest_pin(pin=target, output_dir=output_dir, query_slug=query, index=idx)
                w = target.get("width")
                h = target.get("height")
                ar = round(w / h, 4) if w and h else None
                res = {
                    "index": idx,
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
            send_response({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]}})

        elif tool_name == "pinterest_fetch":
            limit = int(arguments.get("limit", 3))
            output_dir = arguments.get("output", ".")
            raw_pins = search_public_pinterest(query=query, limit=limit)
            downloaded = []
            for i, p in enumerate(raw_pins, start=1):
                try:
                    sp = download_pinterest_pin(pin=p, output_dir=output_dir, query_slug=query, index=i)
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
                except Exception as e:
                    pass
            out = {"ok": True, "command": "fetch", "source": "pinterest", "query": query, "count": len(downloaded), "downloaded": downloaded}
            send_response({"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]}})
        else:
            send_response({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}})

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            handle_request(req)
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
