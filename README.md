# 📌 ClipSearch - Pinterest CLI & AI Agent Integration

`clipsearch` is a fast, agent-friendly command-line tool and **Model Context Protocol (MCP)** server for searching public Pinterest pins and downloading high-resolution reference photos.

It works both as a standalone **Terminal CLI** and as a native **AI Agent Tool** for [Hermes Agent](https://github.com/nousresearch/hermes-agent).

---

## ⚡ Quick Setup (Easy 2-Minute Guide)

### Step 1: Install `clipsearch`
Open your Mac terminal and run:

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

### Step 2: Connect to Hermes Agent (Optional)

If you use **Hermes Agent** (Web UI, Desktop App, or TUI), add `clipsearch` as a native MCP tool:

1. Open your Hermes configuration file:
   ```bash
   nano ~/.hermes/config.yaml
   ```

2. Add `pinterest_cli` under the `mcp_servers` section:

```yaml
mcp_servers:
  pinterest_cli:
    command: python3
    args:
      - /Users/ariqserazi/Projects2/pintrestCli/app/mcp_server.py
    defer: false
```

3. Restart Hermes or click **"New Session"** (`Cmd + N`) in the Hermes UI!

---

## 🚀 How to Use (CLI Examples)

### 1. Search Pinterest Pins
Find photos, titles, pin URLs, image dimensions, and aspect ratios:

```bash
clipsearch pinterest search "abandoned Japanese shopping mall" --limit 5 --json --pretty
```

### 2. Download a Specific Image
Download result `#1` from search results into an `./images` folder:

```bash
clipsearch pinterest download --query "abandoned Japanese shopping mall" --index 1 --output ./images --json --pretty
```

### 3. Batch Fetch & Download Photos
Search and download top 3 photos directly to disk in one command:

```bash
clipsearch pinterest fetch "cyberpunk Tokyo night" --limit 3 --output ./photos --json --pretty
```

---

## 🤖 How AI Agents Use It

When connected to Hermes Agent, you can simply ask naturally in plain English:

> 💬 **You**: *"Find me 3 visual reference photos of abandoned Japanese shopping malls."*
>
> 🤖 **Hermes**: 
> 1. Calls `pinterest_search("abandoned Japanese shopping mall")`
> 2. Evaluates the top high-resolution pins.
> 3. Downloads them to disk and presents the image links & descriptions to you automatically!

---

## 🛠️ Project Structure

| File | Description |
| --- | --- |
| `app/cli.py` | Command-line tool dispatcher (`clipsearch`) |
| `app/mcp_server.py` | FastMCP Server for native AI Agent integration |
| `app/pinterest_client.py` | Public Pinterest scraping & high-res image downloader |
| `hermes/pinterest-image-search/SKILL.md` | Hermes Agent skill definition |
| `tests/test_cli_pinterest.py` | Unit test suite |

---

## 🧪 Testing

Run unit tests to ensure everything is working:

```bash
python3 -m unittest tests/test_cli_pinterest.py tests/test_pinterest.py
```
