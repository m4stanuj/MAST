---
name: video-gen
description: Video editing MCP - trim, merge, add text, effects (NOT generation)
---

# Video Editing MCP — kil化/mcp-video

**1.2k+ stars** | Video editing tools | Fully free | No API keys needed

## ⚠️ IMPORTANT: This is VIDEO EDITING, not VIDEO GENERATION

This MCP provides video **editing** capabilities:
- Trim, merge, split videos
- Add text overlays
- Apply effects and filters
- Resize, crop, rotate
- Extract audio
- Convert formats

**For video generation**, you would need API keys (DALL-E, Runway, Kling, etc.)

---

## Quick Start

### Install (already done!)
```bash
pip install mcp-video
```

### Verified Command
```bash
python -m mcp_video --mcp
```

### Status: ✅ WORKING

---

## Features

### Editing Operations
- `trim` - Cut video segments
- `merge` - Combine multiple videos
- `split` - Split video into parts

### Text & Graphics
- `add-text` - Overlay text on video
- `watermark` - Add image watermark
- `subtitles` - Burn subtitles

### Effects
- `filter` - Apply visual filters
- `blur` - Blur regions
- `color-grade` - Color grading
- `chroma-key` - Green screen removal

### Format & Quality
- `convert` - Convert format (MP4, AVI, WebM, etc.)
- `resize` - Change resolution
- `speed` - Change playback speed
- `thumbnail` - Extract preview frame

### Audio
- `add-audio` - Add/replace audio track
- `extract-audio` - Extract audio to file
- `normalize-audio` - Normalize loudness

---

## Common Commands

```bash
# Get video info
python -m mcp_video info video.mp4

# Trim video (start second, end second)
python -m mcp_video trim input.mp4 --start 5 --end 10 --output trimmed.mp4

# Add text overlay
python -m mcp_video add-text input.mp4 --text "Hello World" --output output.mp4

# Convert format
python -m mcp_video convert input.mp4 --format webm --output output.webm

# Extract audio
python -m mcp_video extract-audio input.mp4 --output audio.mp3
```

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Functionality | ✅ 9/10 |
| Stars | 1.2k ⭐ |
| Ease of Use | 8/10 |

**Overall: 9/10** — Best free video editing MCP!

## Requirements

- Python 3.8+
- FFmpeg (for video processing)
- opencv-python (installed automatically)

---

## Installation (if needed)

```bash
pip install mcp-video

# For FFmpeg (Windows with Chocolatey)
choco install ffmpeg

# For FFmpeg (Mac)
brew install ffmpeg

# For FFmpeg (Linux)
sudo apt install ffmpeg
```