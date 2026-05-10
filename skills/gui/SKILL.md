---
name: gui
description: GUI automation - mouse, keyboard, window control, screenshot, OCR
---

# GUI Control MCP — gui_mcp.py

**Full GUI automation:** Mouse, keyboard, windows, screenshots, OCR, template matching

---

## Quick Start

### Install (dependencies already installed)
```bash
pip install pyautogui pygetwindow Pillow psutil pyperclip
pip install opencv-python numpy  # optional: find_on_screen
pip install pytesseract         # optional: ocr_screen
```

### Verified Command
```bash
python C:/workk/gui_mcp/gui_mcp.py
```

### Status: ✅ WORKING

---

## Features

### Mouse Control
- `mouse_click` - Click at coordinates
- `mouse_move` - Move mouse
- `mouse_drag` - Drag from point A to B
- `mouse_scroll` - Scroll up/down

### Keyboard Control
- `keyboard_type` - Type text (unicode safe)
- `keyboard_hotkey` - Key combinations (ctrl+c, alt+tab, etc.)
- `keyboard_press` - Single key press

### Window Management
- `window_list` - List all open windows
- `window_focus` - Bring window to front
- `window_resize` - Resize window
- `window_minimize` / `window_maximize`
- `wait_for_window` - Wait until window appears

### Screenshot & OCR
- `screenshot` - Full screen or region
- `ocr_screen` - Extract text from screen
- `find_on_screen` - Template matching

### Other
- `app_launch` / `app_kill` - Launch/kill applications
- `clipboard_set` / `clipboard_get` - Clipboard
- `process_list` - List running processes

---

## Usage Examples

### Click at coordinates
```
mouse_click(x=500, y=300, button="left", clicks=1)
```

### Type text
```
keyboard_type(text="Hello World")
```

### Screenshot
```
screenshot()
# Returns: {"width": 1920, "height": 1080, "base64": "..."}
```

### List windows
```
window_list()
# Returns: {"count": 10, "windows": [{"title": "Chrome", ...}]}
```

### Focus window
```
window_focus(title="Notepad")
```

---

## MCP Config

```jsonc
{
  "mcp": {
    "gui": {
      "command": ["python", "C:/workk/gui_mcp/gui_mcp.py"],
      "enabled": true
    }
  }
}
```

---

## Requirements

- Windows/macOS/Linux
- Python 3.8+
- pyautogui, pygetwindow, Pillow, psutil, pyperclip

---

## Rating

| Feature | Score |
|---------|-------|
| Free | ✅ 10/10 |
| Functionality | ✅ 10/10 |
| GUI Automation | ✅ 10/10 |
| OCR | ✅ 8/10 |

**Overall: 10/10** — Essential for GUI automation!