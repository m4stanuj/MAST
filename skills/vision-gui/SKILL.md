---
name: vision-gui
description: AI-powered GUI control - vision-guided automation (needs GEMINI_API_KEY)
---

# Vision GUI MCP — vision_gui_mcp.py

**AI-powered GUI automation:** Describe what you want in natural language, AI controls your screen!

---

## ⚠️ IMPORTANT: Requires API Key

This MCP uses vision AI to understand screen and interact. You need:

### Get Free API Keys

1. **Gemini (Recommended):**
   - Go to: https://aistudio.google.com/apikey
   - Create new API key
   - Add to `C:/workk/gui_mcp/.env`:
     ```
     GEMINI_API_KEY=your_key_here
     ```

2. **Groq (Fallback):**
   - Go to: https://console.groq.com/keys
   - Create new key
   - Add to `.env`:
     ```
     GROQ_API_KEY=your_key_here
     ```

---

## Quick Start

### Install (dependencies already installed)
```bash
pip install pyautogui Pillow requests pyperclip python-dotenv
```

### Verified Command
```bash
python C:/workk/gui_mcp/vision_gui_mcp.py
```

### Status: ⚠️ Requires GEMINI_API_KEY

---

## Features (Claude CU Style!)

### Vision Tools
- `vision_click` - "Click the Submit button" - AI finds and clicks
- `vision_type` - "Type 'hello' in search box" - AI finds field and types
- `vision_find` - Find coordinates without clicking
- `vision_wait_for` - Wait until element appears
- `vision_verify` - "Is the dialog closed?" - Verify UI state

### High-Level Tasks
- `do_task` - "Go to Google and search for cats" - Complex automation
- `describe_screen` - "What's on this screen?" - Get AI description

---

## Usage Examples

### Click using natural language
```
vision_click(target="Click the Submit button")
```

### Type in a field
```
vision_type(target="Search input", text="artificial intelligence")
```

### Find something
```
vision_find(target="The login button")
```

### Describe screen
```
describe_screen(question="What form fields are visible?")
```

### Complex task
```
do_task(task="Fill out the contact form with name John, email john@example.com")
```

---

## MCP Config

```jsonc
{
  "mcp": {
    "vision-gui": {
      "command": ["python", "C:/workk/gui_mcp/vision_gui_mcp.py"],
      "enabled": true
    }
  }
}
```

---

## How It Works

1. **Take screenshot** → Send to Gemini/Groq vision model
2. **Analyze** → AI understands the UI and decides action
3. **Execute** → AI returns coordinates, we click/type
4. **Verify** → Optionally verify success

---

## Requirements

- Python 3.8+
- pyautogui, Pillow, requests, pyperclip, python-dotenv
- **GEMINI_API_KEY** or **GROQ_API_KEY** in .env

---

## Rating

| Feature | Score |
|---------|-------|
| Free (API key) | ✅ 10/10 |
| AI-Powered | ✅ 10/10 |
| Ease of Use | ✅ 9/10 |
| Claude CU Style | ✅ 10/10 |

**Overall: 10/10** — Game changer for GUI automation!

---

## Common Issues

| Issue | Solution |
|-------|----------|
| No API key | Add GEMINI_API_KEY to C:/workk/gui_mcp/.env |
| Vision not finding element | Use more descriptive target text |
| Slow response | Try Groq (faster than Gemini) |
| Click coords wrong | Resize your screen or adjust MAX_WIDTH |