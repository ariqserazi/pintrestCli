# 📌 ClipSearch - Pinterest & YouTube Downloader CLI & AI Agent Integration

`clipsearch` is a fast, agent-friendly command-line tool and **Model Context Protocol (MCP)** server for searching and downloading content from **Pinterest** (high-res images) and **YouTube** (videos and audio clips).

It works both as a standalone **Terminal CLI** and as a native **AI Agent Tool** for [Hermes Agent](https://github.com/nousresearch/hermes-agent) installed on your device.

---

## ⚡ Quick Setup (Easy 2-Minute Guide)

### Step 1: Install `clipsearch`
Open your terminal and run:

```bash
git clone https://github.com/ariqserazi/pintrestCli.git
cd pintrestCli
pip install -e .
```

Verify the installation:
```bash
clipsearch --help
```

---

### Step 2: Connect to Hermes Agent (Installed on Device)

Add `clipsearch` as a native MCP server in your local Hermes configuration:

1. Open your Hermes configuration file:
   ```bash
   nano ~/.hermes/config.yaml
   ```

2. Add `pinterest_cli` (which handles both Pinterest & YouTube tools) under `mcp_servers`:

```yaml
mcp_servers:
  pinterest_cli:
    command: /Users/ariqserazi/.hermes/hermes-agent/venv/bin/python
    args:
      - /Users/ariqserazi/Projects2/pintrestCli/app/mcp_server.py
    defer: false
```

3. Restart Hermes or click **"New Session"** (`Cmd + N`) in the Hermes UI!

---

## 🚀 How to Use (CLI Examples)

### 📸 Pinterest Commands

#### 1. Search Pinterest Pins
Find photos, titles, pin URLs, image dimensions, and aspect ratios:
```bash
clipsearch pinterest search "abandoned Japanese shopping mall" --limit 5 --json --pretty
```

#### 2. Download a Specific Image
Download result `#1` from search results into an `./images` folder:
```bash
clipsearch pinterest download --query "abandoned Japanese shopping mall" --index 1 --output ./images --json --pretty
```

#### 3. Batch Fetch & Download Photos
Search and download top 3 photos directly to disk in one command:
```bash
clipsearch pinterest fetch "cyberpunk Tokyo night" --limit 3 --output ./photos --json --pretty
```

---

### 🎥 YouTube Commands

#### 1. Search YouTube Videos
Find video titles, channel name, duration, view count, and URLs:
```bash
clipsearch youtube search "Python tutorial in 100 seconds" --limit 3 --json --pretty
```

#### 2. Download Video or Audio Clip (MP4 or MP3)
Download video result `#1` as 720p MP4 or audio MP3 into `./videos`:
```bash
# Download MP4 Video
clipsearch youtube download --query "Python tutorial in 100 seconds" --index 1 --output ./videos --format mp4 --quality 720 --json --pretty

# Download MP3 Audio Only
clipsearch youtube download --query "lofi hip hop beats" --index 1 --output ./music --format mp3 --json --pretty
```

#### 3. Batch Fetch YouTube Videos
Search and download top 2 YouTube videos directly to disk:
```bash
clipsearch youtube fetch "blender 3d beginner tutorial" --limit 2 --output ./tutorials --json --pretty
```

---

## 🤖 How Hermes Agent Uses It

When connected to Hermes Agent on your device, you can ask naturally in plain English:

> 💬 **You**: *"Search YouTube for Python tutorials in 100 seconds and download the first video as an MP4."*
>
> 🤖 **Hermes**: 
> 1. Calls `youtube_search("Python tutorial in 100 seconds")`
> 2. Calls `youtube_download(query="Python tutorial in 100 seconds", index=1, format="mp4")`
> 3. Saves the video file to disk and presents the file path to you!

---

## 🛠️ Project Structure

| File | Description |
| --- | --- |
| `app/cli.py` | Command-line tool dispatcher (`clipsearch`) |
| `app/mcp_server.py` | FastMCP Server for native Hermes AI Agent integration |
| `app/pinterest_client.py` | Pinterest public search & image downloader |
| `app/youtube_client.py` | YouTube search & `yt-dlp` video/audio downloader |
| `hermes/pinterest-image-search/SKILL.md` | Hermes Agent Pinterest skill definition |
| `hermes/youtube-video-downloader/SKILL.md` | Hermes Agent YouTube skill definition |
| `tests/` | Unit tests for CLI, Pinterest, and YouTube features |

---

## 🧪 Testing

Run all unit tests:

```bash
python3 -m unittest tests/test_youtube.py tests/test_cli_pinterest.py tests/test_pinterest.py
```
