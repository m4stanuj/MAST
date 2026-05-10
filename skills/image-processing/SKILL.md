---
name: image-processing
description: Full image manipulation - resize, crop, filters, convert
---

# Image Processing MCP — sunriseapps/imagesorcery-mcp

**295 stars** | Full image manipulation | Fully free

## Quick Start

### Install (already done!)
```bash
pip install imagesorcery-mcp
```

### Verified Command
```bash
python -m imagesorcery_mcp --transport stdio
```

### Status: ✅ WORKING

### Configuration (opencode.jsonc)
```jsonc
{
  "mcp": {
    "image-processing": {
      "command": ["pip", "install", "imagesorcery-mcp"]
    }
  }
}
```

## Features

### Basic Operations
- Resize images
- Crop images
- Rotate images
- Flip images

### Filters
- Blur
- Sharpen
- Grayscale
- Sepia
- Brightness/Contrast

### Format Conversion
- JPEG ↔ PNG ↔ WebP ↔ GIF
- Quality adjustment
- Compression

### Advanced
- Watermarks
- Text overlay
- Shapes (rectangles, circles)
- Compositing

## Tools Available

- `resize_image` - Resize to dimensions
- `crop_image` - Crop to area
- `apply_filter` - Apply filter
- `convert_format` - Convert format
- `add_watermark` - Add watermark
- `add_text` - Add text overlay

## Usage Example

```python
# Resize
await resize_image(
    input="photo.jpg",
    output="thumb.png",
    width=200,
    height=200
)

# Apply filter
await apply_filter(
    input="photo.jpg",
    output="blurred.jpg",
    filter="blur"
)

# Convert format
await convert_format(
    input="photo.jpg",
    output="photo.webp",
    quality=85
)
```

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Functionality | ✅ 9/10 |
| Stars | 295 ⭐ |
| Ease of Use | 9/10 |

**Overall: 9/10** — Best free image processing!

## Requirements

- Python 3.8+
- Pillow library (installed automatically)

---
