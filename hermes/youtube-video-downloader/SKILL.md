---
name: youtube-video-downloader
description: Search YouTube videos and download video or audio clips using clipsearch CLI or youtube MCP tools.
---

# YouTube Video & Audio Downloader

Use ClipSearch YouTube tools whenever the user asks for YouTube videos, video clips, video downloads, audio extractions, music clips, tutorials, or YouTube content.

## Search YouTube Videos

Run:
```bash
clipsearch youtube search "<descriptive query>" --limit 5 --json
```

Read the returned JSON to inspect video titles, duration, uploader, view count, and video URLs.

## Download a Specific Video or Audio

Run:
```bash
clipsearch youtube download \
  --query "<same query>" \
  --index <result number> \
  --output <working directory> \
  --format <mp4|mp3> \
  --quality <720|1080> \
  --json
```

## Batch Download Top YouTube Videos

Run:
```bash
clipsearch youtube fetch \
  "<descriptive query>" \
  --limit 3 \
  --output <working directory> \
  --format <mp4|mp3> \
  --quality 720 \
  --json
```

## Rules

- Preserve `video_url` and `uploader` metadata.
- Respect user format requests (`mp4` for video, `mp3` for audio).
- Default to `720p` video quality for balanced speed and size.
- Ensure destination directories exist before saving.
