---
name: asset-gen-local
description: LOCAL AI asset generation - image+music+speech+3D - NO API KEY NEEDED!
---

# Local Asset Gen MCP — davidemodolo/local-asset-gen-mcp

**✅ FULLY LOCAL - NO API KEY NEEDED!** | Image + Music + Speech + 3D Generation

## ⚠️ IMPORTANT PREREQUISITES

Before using this MCP, you MUST:

### 1. Accept HuggingFace Licenses

- Go to: https://huggingface.co/stabilityai/stable-audio-open-1.0
- Click **"Accept Terms"** button (required for music generation)

### 2. Get HuggingFace Token

- Go to: https://huggingface.co/settings/tokens
- Create new token (read access)
- Run: 
  ```
  C:/workk/local-asset-gen-mcp/.venv/Scripts/python.exe -c "from huggingface_hub import login; login('YOUR_TOKEN')"
  ```

---

## Quick Start

### Install (already done!)
- Repository cloned at: `C:/workk/local-asset-gen-mcp`
- Virtual env at: `C:/workk/local-asset-gen-mcp/.venv`
- Dependencies: ✅ Installed

### Verify MCP works
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | C:/workk/local-asset-gen-mcp/.venv/Scripts/python.exe C:/workk/local-asset-gen-mcp/mcp_server/main.py
```

---

## Features (All FREE!)

### 🖼️ Image Generation
- **Model:** SSD-1B (fast, distilled SDXL)
- **Tool:** `generate_image`
- **Prompt-based text-to-image**
- Resolution: 512x512 to 1024x1024

### 🎵 Music Generation
- **Model:** Stable Audio Open
- **Tool:** `generate_audio`
- **Text-to-music/sound effects**
- Duration: 5-30 seconds
- **⚠️ Requires license acceptance on HF**

### 🗣️ Speech Generation
- **Model:** Qwen3-TTS
- **Tool:** `generate_speech`
- **Text-to-speech**
- Multiple voices available
- Multilingual support

### 🎲 3D Model Generation
- **Model:** TripoSR
- **Tool:** `generate_3d_model`
- **Image-to-3D** or **Text-to-3D**
- Output: GLB or OBJ format

---

## MCP Config (opencode.jsonc)

```jsonc
{
  "mcp": {
    "asset-gen-local": {
      "command": [
        "C:/workk/local-asset-gen-mcp/.venv/Scripts/python.exe",
        "C:/workk/local-asset-gen-mcp/mcp_server/main.py"
      ],
      "enabled": true
    }
  }
}
```

---

## Usage Examples

### Generate Image
```
generate_image(
  prompts=["a cute cat sitting on a sofa"],
  width=512,
  height=512,
  steps=20
)
```

### Generate Music
```
generate_audio(
  prompt="upbeat electronic dance music with strong bass",
  duration=10
)
```

### Generate Speech
```
generate_speech(
  text="Hello! This is a test of the text to speech system.",
  voice="female_2",
  language="en"
)
```

### Generate 3D Model
```
generate_3d_model(
  prompt="a beautiful vase",
  output_format="glb"
)
```

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Local (no API) | ✅ 10/10 |
| Image Gen | ✅ 9/10 |
| Music Gen | ✅ 8/10 |
| Speech Gen | ✅ 8/10 |
| 3D Gen | ✅ 7/10 |
| Setup Required | ⚠️ 6/10 |

**Overall: 9/10** — Best fully free local asset generation!

---

## Requirements

- **GPU:** NVIDIA 8GB+ VRAM (RTX 2060 Super works ✅)
- **Python:** 3.10+
- **HF Token:** Required for model downloads
- **License:** Accept Stable Audio Open terms

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Model download slow | First run is slow - normal |
| GPU OOM | Reduce resolution to 512x512 |
| Token error | Run `huggingface_hub.login()` with your token |
| License error | Accept terms at https://huggingface.co/stabilityai/stable-audio-open-1.0 |

---

## Output Directories

- Images: `C:/workk/local-asset-gen-mcp/generated_images/`
- Audio: `C:/workk/local-asset-gen-mcp/generated_audio/`
- 3D Models: `C:/workk/local-asset-gen-mcp/generated_models/`

---

## Status

- ✅ MCP server initialized successfully
- ⚠️ Requires HuggingFace token for model downloads
- ⚠️ Requires license acceptance for music generation
- ✅ Enabled in opencode.jsonc