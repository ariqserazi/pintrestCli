# ClipSearch - Pinterest CLI

An agent-friendly Python CLI (`clipsearch`) designed for autonomous invocation by **Hermes Agent** (or human terminal users) to search public Pinterest pins and download high-resolution images.

---

## Overview

`clipsearch` provides a fast, structured command-line interface for querying Pinterest and downloading pin images directly without requiring browser interaction or API credentials.

### Features
- **Public Pinterest Search**: Search public pins with plain-language queries.
- **Machine-Readable Output**: Strict `--json` output mode tailored for AI agents (like Hermes Agent).
- **High-Resolution Selection**: Prefers original / highest resolution image variants available.
- **1-Based Result Indexing**: Easily inspect search results and request specific candidates by index (`1`, `2`, `3`, etc.).
- **Deterministic File Naming**: Saves files predictably as `<query-slug>-<index:02d>-<pin-id>.<extension>`.
- **Hermes Agent Skill**: Ready-to-use skill definition in `hermes/pinterest-image-search/SKILL.md`.

---

## Installation

Install the package in your active Python environment:

```bash
python3 -m pip install -e .
```

Verify installation:

```bash
clipsearch --help
```

---

## CLI Usage

### 1. Search Pinterest Pins

Search for public pins and return metadata (titles, descriptions, pin URLs, image URLs, dimensions, aspect ratio).

```bash
clipsearch pinterest search "<query>" [--limit LIMIT] [--json] [--pretty]
```

**Examples**:
```bash
# Formatted JSON output for agents (returns top 5 results)
clipsearch pinterest search "abandoned Japanese mall" --limit 5 --json --pretty

# Human-readable terminal output
clipsearch pinterest search "cyberpunk Tokyo night" --limit 8
```

#### Search JSON Response Format:
```json
{
  "ok": true,
  "command": "search",
  "source": "pinterest",
  "query": "abandoned Japanese mall",
  "count": 2,
  "results": [
    {
      "index": 1,
      "pin_id": "1100567227722655904",
      "title": "Abandoned Shopping Mall | Post-Apocalyptic Concept Art",
      "description": "You are alone in an abandoned Shopping Mall, what are you doing?",
      "pinner": "ArtDreams092",
      "width": 736,
      "height": 1308,
      "aspect_ratio": 0.5627,
      "pin_url": "https://www.pinterest.com/pin/1100567227722655904/",
      "image_url": "https://i.pinimg.com/originals/fa/d2/6b/fad26b6bda9692df82c71d077882e9c8.jpg",
      "local_path": null
    }
  ]
}
```

---

### 2. Download a Specific Pin

Search Pinterest and download a specific image result by its 1-based `--index`.

```bash
clipsearch pinterest download --query "<query>" --index <1-based index> [--output OUTPUT_DIR] [--json] [--pretty]
```

**Example**:
```bash
clipsearch pinterest download \
  --query "abandoned Japanese mall" \
  --index 1 \
  --output ./images \
  --json \
  --pretty
```

#### Download JSON Response Format:
```json
{
  "ok": true,
  "command": "download",
  "source": "pinterest",
  "query": "abandoned Japanese mall",
  "result": {
    "index": 1,
    "pin_id": "1100567227722655904",
    "title": "Abandoned Shopping Mall",
    "description": "...",
    "pinner": "ArtDreams092",
    "width": 736,
    "height": 1308,
    "aspect_ratio": 0.5627,
    "pin_url": "https://www.pinterest.com/pin/1100567227722655904/",
    "image_url": "https://i.pinimg.com/originals/fa/d2/6b/fad26b6bda9692df82c71d077882e9c8.jpg",
    "local_path": "images/abandoned-japanese-mall-01-1100567227722655904.jpg"
  }
}
```

---

### 3. Fetch Batch of Images

Convenience command to search and download a batch of images at once.

```bash
clipsearch pinterest fetch "<query>" [--limit LIMIT] [--output OUTPUT_DIR] [--json] [--pretty]
```

**Example**:
```bash
clipsearch pinterest fetch "cyberpunk Tokyo night" --limit 5 --output ./images --json --pretty
```

#### Fetch JSON Response Format:
```json
{
  "ok": true,
  "command": "fetch",
  "source": "pinterest",
  "query": "cyberpunk Tokyo night",
  "requested": 5,
  "downloaded": 5,
  "results": [
    {
      "index": 1,
      "pin_id": "...",
      "title": "...",
      "description": "...",
      "pin_url": "...",
      "image_url": "...",
      "width": 1080,
      "height": 1920,
      "local_path": "images/cyberpunk-tokyo-night-01-5840674511525632.jpg"
    }
  ],
  "errors": []
}
```

---

## Hermes Agent Integration

Hermes Agent can call `clipsearch` via its terminal capability.

### 1. Install Hermes Skill

Copy the skill definition from the repository directory into your Hermes Agent skills directory:

```bash
mkdir -p ~/.hermes/skills/
cp -r ~/Projects2/pintrestCli/hermes/pinterest-image-search ~/.hermes/skills/
```

Or from inside the repository directory:

```bash
cd ~/Projects2/pintrestCli
cp -r hermes/pinterest-image-search ~/.hermes/skills/
```

### 2. Example Interaction

- **User**: *"Find me three moody photographs of abandoned malls."*
- **Hermes**:
  1. Searches Pinterest:
     ```bash
     clipsearch pinterest search "moody abandoned shopping mall interior photography" --limit 10 --json
     ```
  2. Evaluates returned JSON metadata (title, dimensions, aspect ratio, source URL).
  3. Downloads selected candidates:
     ```bash
     clipsearch pinterest download --query "moody abandoned shopping mall interior photography" --index 1 --output ./images --json
     ```
  4. Inspects downloaded images when vision capability is available and presents source metadata (`pin_url`) to the user.

---

## Error Codes & Exit Statuses

In `--json` mode, errors are returned strictly formatted as JSON to stdout with no traceback output.

```json
{
  "ok": false,
  "error": {
    "code": "PINTEREST_SEARCH_FAILED",
    "message": "Pinterest search failed.",
    "details": "..."
  }
}
```

| Exit Code | Code | Cause |
| --- | --- | --- |
| `0` | Success | Operation completed successfully |
| `2` | `INVALID_ARGUMENT` | Missing or invalid CLI arguments (e.g. limit out of range) |
| `1` | `INVALID_INDEX` | Requested index exceeds total results found |
| `1` | `NO_RESULTS` | Search returned 0 matching pins |
| `1` | `PINTEREST_SEARCH_FAILED` | Network or parsing failure during search |
| `1` | `PINTEREST_DOWNLOAD_FAILED` | Network or parsing failure during download |
| `1` | `FILESYSTEM_ERROR` | Error writing downloaded image to disk |
| `1` | `NETWORK_ERROR` | Transport timeout or connection error |

---

## Development & Testing

Run unit tests:

```bash
python3 -m unittest tests/test_cli_pinterest.py tests/test_pinterest.py
```

### Project Structure

| Path | Purpose |
| --- | --- |
| `app/cli.py` | CLI entrypoint (`clipsearch`) and argument parser |
| `app/pinterest_client.py` | Pinterest public web scraper and image downloader |
| `hermes/pinterest-image-search/SKILL.md` | Hermes Agent skill definition |
| `tests/test_cli_pinterest.py` | Unit tests for CLI functionality |
| `pyproject.toml` | Packaging configuration |
