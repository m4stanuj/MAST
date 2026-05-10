"""
vision_mcp.py — OpenWork Vision MCP Server
==========================================
Backend: llama-server (OpenAI-compatible /v1/chat/completions)
         Runs locally, supports any GGUF vision model (Qwen3-VL, LLaVA, etc.)

NO OLLAMA. llama-server only.

Setup (run once):
  # Download llama-server from https://github.com/ggerganov/llama.cpp/releases
  # Download your GGUF model + mmproj file, then:
  llama-server.exe ^
    --model         models/qwen3-vl-7b-q4.gguf ^
    --mmproj        models/qwen3-vl-7b-mmproj.gguf ^
    --host          0.0.0.0 ^
    --port          8080 ^
    --n-gpu-layers  35 ^
    --ctx-size      4096

Env vars (optional overrides):
  LLAMA_URL      default: http://localhost:8080
  VISION_MODEL   default: qwen3-vl-fast   (model name sent in API calls — cosmetic for llama-server)
  SCREEN_W       default: 1920
  SCREEN_H       default: 1080

Text-only fallback (when llama-server offline):
  Automatically uses llm_fallback.py chain (Groq → Cerebras → Gemini → ...)

Changes from v6:
  - Removed ALL ollama imports, references, and _vision_ollama was renamed to _vision_llama
  - Function name: _vision_ollama → _vision_llama  (same logic, cleaner name)
  - OFFLINE sentinel changed from "OLLAMA_OFFLINE" → "LLAMA_OFFLINE" for clarity
  - health_check: removed Ollama section, added llama-server model list + mmproj hint
  - Comments updated throughout
  - No behavioral changes to screenshot, coordinate scaling, fallback, pyautogui
"""

import asyncio
import base64
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from io import BytesIO
from mcp.server import Server
from mcp.server.stdio import stdio_server

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False

LLAMA_URL    = os.getenv("LLAMA_URL",    "http://localhost:8080")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen3-vl-fast")
SCREEN_W     = int(os.getenv("SCREEN_W", "1920"))
SCREEN_H     = int(os.getenv("SCREEN_H", "1080"))

app = Server("vision-qwen")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_error(val) -> bool:
    """Safe check — handles both str and non-str returns from _screenshot."""
    return isinstance(val, str) and val.startswith("ERROR")


def _screenshot() -> tuple:
    """
    Returns (base64_str, scale_factor).
    scale = actual_screen_px / resized_image_px
    So: screen_coord = image_coord * scale
    """
    try:
        import mss
        from PIL import Image
        with mss.mss() as sct:
            mon = sct.monitors[1]
            raw = sct.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            scale = 1.0
            if img.width > 1280:
                scale = img.width / 1280
                new_h = int(img.height / scale)
                img = img.resize((1280, new_h), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode(), scale
    except ImportError as e:
        return f"ERROR: Missing dependency — {e} | Fix: pip install mss pillow", 1.0
    except Exception as e:
        return f"ERROR: Screenshot failed — {e}", 1.0


def _vision_llama(prompt: str, b64: str) -> str:
    """
    Call vision model via llama-server (OpenAI-compatible /v1/chat/completions).
    Returns response text, or sentinel strings on failure:
      "LLAMA_OFFLINE"   — server not running
      "ERROR: ..."      — other failure
    """
    if not _REQUESTS_OK:
        return "LLAMA_OFFLINE"
    try:
        r = requests.post(
            f"{LLAMA_URL}/v1/chat/completions",
            json={
                "model": VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1024,
                "stream": False,
            },
            timeout=90,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        return "LLAMA_OFFLINE"
    except requests.exceptions.Timeout:
        return "ERROR: Vision timeout (90s) — model cold start, retry in 30s"
    except Exception as e:
        return f"ERROR: llama-server call failed — {e}"


def _text_fallback(prompt: str) -> str:
    """Text-only fallback via llm_fallback chain (no image, cloud APIs)."""
    try:
        from llm_fallback import chat_complete
        return chat_complete([{"role": "user", "content": prompt}])
    except ImportError:
        return "ERROR: llm_fallback.py not found — place it in the same directory as vision_mcp.py"
    except Exception as e:
        return f"ERROR: Fallback LLM failed — {e}"


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@app.tool()
async def screen_analyze(question: str = "Screen pe kya dikh raha hai?") -> str:
    """Take screenshot and analyze with vision model via llama-server. Falls back to text LLM if offline."""
    b64, _ = _screenshot()
    if _is_error(b64):
        return b64
    prompt = (
        f"Analyze this computer screen carefully. Answer in the same language as the question.\n"
        f"Question: {question}\n"
        f"Be precise about element locations (top-left, center, bottom-right, coordinates if visible)."
    )
    result = _vision_llama(prompt, b64)
    if result == "LLAMA_OFFLINE":
        fallback_prompt = (
            f"[Vision unavailable — llama-server offline]\n"
            f"Question about screen: {question}\n"
            f"Explain that you cannot see the screen, and ask the user to describe what they see "
            f"or start llama-server with the correct --model and --mmproj flags."
        )
        return "⚠️ llama-server offline — using text fallback:\n" + _text_fallback(fallback_prompt)
    return result


@app.tool()
async def find_element(element_description: str) -> str:
    """Find UI element on screen. Returns SCREEN-SCALED coordinates ready for pyautogui."""
    b64, scale = _screenshot()
    if _is_error(b64):
        return b64
    img_w = int(SCREEN_W / scale)
    img_h = int(SCREEN_H / scale)

    prompt = (
        "Find this UI element on screen: " + element_description + "\n\n"
        "If found, respond ONLY with this JSON:\n"
        '{"found": true, "x": <int>, "y": <int>, "confidence": <0.0-1.0>, "description": "<text>"}\n\n'
        "If not found:\n"
        '{"found": false, "description": "<what you see instead>"}\n\n'
        f"Image size: {img_w}x{img_h}. x,y = CENTER of element. JSON only, no extra text."
    )
    result = _vision_llama(prompt, b64)
    if result == "LLAMA_OFFLINE":
        return "ERROR: llama-server offline — find_element needs vision model. Start llama-server first."
    try:
        m = re.search(r'\{.*?\}', result, re.DOTALL)
        if m:
            d = json.loads(m.group())
            if d.get("found"):
                x_screen = int(d.get("x", 0) * scale)
                y_screen = int(d.get("y", 0) * scale)
                return (
                    f"FOUND: {d.get('description')}\n"
                    f"Screen Coordinates: X={x_screen}, Y={y_screen}\n"
                    f"Confidence: {d.get('confidence', '?')}\n"
                    f"To click: pyautogui.click({x_screen}, {y_screen})"
                )
            return f"NOT FOUND: {d.get('description', 'Element not visible on screen')}"
    except json.JSONDecodeError:
        pass
    return f"Model response (parse failed):\n{result}"


@app.tool()
async def screen_ocr(region: str = "full") -> str:
    """Extract all text from screen. Hindi + English. region: full/top/center/bottom"""
    valid_regions = ("full", "top", "center", "bottom")
    if region not in valid_regions:
        region = "full"
    b64, _ = _screenshot()
    if _is_error(b64):
        return b64
    hint = f"Focus only on the {region} portion of the screen." if region != "full" else ""
    prompt = (
        f"Extract ALL visible text from this screen screenshot. Include every language (Hindi, English, etc).\n"
        f"{hint}\n"
        f"Return text exactly as it appears — buttons, labels, menus, errors, URLs, input fields, everything.\n"
        f"Format: preserve layout where possible."
    )
    result = _vision_llama(prompt, b64)
    if result == "LLAMA_OFFLINE":
        return "⚠️ llama-server offline — OCR requires vision model.\n" + _text_fallback(
            f"Vision/OCR unavailable. User wants text extracted from region: '{region}'. "
            f"Explain that llama-server must be running with a vision model for OCR to work."
        )
    return result


@app.tool()
async def describe_current_state() -> str:
    """Get full screen context: which app, what's happening, key elements, next action."""
    b64, _ = _screenshot()
    if _is_error(b64):
        return b64
    prompt = (
        "Analyze this screen screenshot and answer:\n"
        "1. CURRENT APP: Which application or website is open?\n"
        "2. STATE: What is happening right now? (loading, form, error, etc.)\n"
        "3. KEY ELEMENTS: List main interactive elements visible\n"
        "4. RECOMMENDED NEXT ACTION: What's the logical next step to take?"
    )
    result = _vision_llama(prompt, b64)
    if result == "LLAMA_OFFLINE":
        return "⚠️ llama-server offline — using text fallback:\n" + _text_fallback(
            "Vision unavailable (llama-server offline). User asked for current screen state. "
            "Ask them to describe what they see, or tell them to start llama-server with "
            "--model and --mmproj flags for vision support."
        )
    return result


@app.tool()
async def click_element(element_description: str) -> str:
    """Find element on screen and click it. One-step find + click."""
    if not _PYAUTOGUI_OK:
        return "ERROR: pyautogui not installed — pip install pyautogui"
    find_result = await find_element(element_description)
    if "FOUND:" not in find_result:
        return f"Click failed — element not found:\n{find_result}"
    m = re.search(r'X=(\d+), Y=(\d+)', find_result)
    if not m:
        return f"Click failed — could not parse coordinates from:\n{find_result}"
    x, y = int(m.group(1)), int(m.group(2))
    try:
        pyautogui.click(x, y)
        return f"✅ Clicked at ({x}, {y}) — {element_description}"
    except Exception as e:
        return f"ERROR: pyautogui click failed — {e}"


@app.tool()
async def vision_health_check() -> str:
    """Full system check: llama-server, vision model, screenshot, pyautogui, LLM fallback chain."""
    status = []

    # llama-server check
    if not _REQUESTS_OK:
        status.append("❌ requests not installed — pip install requests")
    else:
        try:
            r = requests.get(f"{LLAMA_URL}/v1/models", timeout=5)
            models = [m["id"] for m in r.json().get("data", [])]
            status.append(f"✅ llama-server: Running at {LLAMA_URL}")
            status.append(f"   Models available: {models or 'NONE (normal for llama-server — model is loaded at startup)'}")
            status.append(f"   Configured VISION_MODEL: {VISION_MODEL}")
            # llama-server doesn't always return model list — test a real call
            status.append(f"   ℹ️  To verify vision: run screen_analyze tool with a test question")
            status.append(f"   ℹ️  If you see image-related errors, check --mmproj flag in your start command")
        except requests.exceptions.ConnectionError:
            status.append(f"❌ llama-server offline (not running at {LLAMA_URL})")
            status.append(f"   Fix — start it like this:")
            status.append(f"     llama-server.exe \\")
            status.append(f"       --model   models/qwen3-vl-7b-q4.gguf \\")
            status.append(f"       --mmproj  models/qwen3-vl-7b-mmproj.gguf \\")
            status.append(f"       --port    8080 \\")
            status.append(f"       --n-gpu-layers 35")
        except Exception as e:
            status.append(f"❌ llama-server error: {e}")

    # Screenshot check
    try:
        b64, scale = _screenshot()
        if not _is_error(b64):
            status.append(f"✅ Screenshot: Working | scale={scale:.2f}x | screen={SCREEN_W}x{SCREEN_H}")
        else:
            status.append(f"❌ Screenshot: {b64}")
    except Exception as e:
        status.append(f"❌ Screenshot: {e}")

    # pyautogui check
    if not _PYAUTOGUI_OK:
        status.append("❌ pyautogui missing: pip install pyautogui")
    else:
        try:
            pos = pyautogui.position()
            status.append(f"✅ pyautogui: Ready | FAILSAFE=True | cursor={pos}")
        except Exception as e:
            status.append(f"⚠️  pyautogui: {e}")

    # LLM fallback chain check
    try:
        from llm_fallback import status_report
        status.append("\n" + status_report())
    except ImportError:
        status.append("⚠️  llm_fallback.py not found — place in same directory as vision_mcp.py")
    except Exception as e:
        status.append(f"⚠️  llm_fallback error: {e}")

    return "\n".join(status)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except (BrokenPipeError, EOFError, OSError):
        pass
    except Exception as e:
        import sys as _sys
        print(f"[vision_mcp] fatal: {e}", file=_sys.stderr)
        _sys.exit(1)
