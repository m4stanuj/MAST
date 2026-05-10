#!/usr/bin/env python3
"""
notify_mcp.py — OpenWork Notification MCP Server v2
=====================================================
DROP-IN INSTALL (no manual config editing needed):

  python notify_mcp.py --install
  → copies self to ~/.config/opencode/
  → patches opencode.json automatically
  → done. Reload workspace.

Backend priority (auto-fallback):
  1. winotify    — best (pip install winotify)
  2. plyer       — cross-platform (pip install plyer)
  3. win10toast  — legacy (pip install win10toast)
  4. PowerShell  — zero deps, built-in Windows
  5. print       — headless fallback, always works

Tools (6):
  notify_done      notify_alert     notify_remind
  notify_progress  notify_history   notify_test
"""

import sys, os, json, time, shutil, threading
from pathlib import Path
from datetime import datetime

_THIS_FILE  = Path(__file__).resolve()
_CONFIG_DIR = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or  os.path.expanduser("~/.config/opencode"))

# Hardened base
sys.path.insert(0, str(_CONFIG_DIR))
sys.path.insert(0, str(Path(__file__).parent))
from _mcp_base import mcp_loop

def _log(m): print(f"[notify_mcp] {m}", file=sys.stderr, flush=True)
def _send(o): print(json.dumps(o, ensure_ascii=False), flush=True)
def _err(rid, msg): _send({"jsonrpc":"2.0","id":rid,"error":{"code":-32000,"message":str(msg)}})

# ─────────────────────────────────────────────────────────────────────
# ANSI HELPERS
# ─────────────────────────────────────────────────────────────────────
_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR")

def _c(code, text):
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"

def _bold(t):    return _c("1", t)
def _dim(t):     return _c("2", t)
def _green(t):   return _c("92", t)
def _yellow(t):  return _c("93", t)
def _cyan(t):    return _c("96", t)
def _red(t):     return _c("91", t)
def _magenta(t): return _c("95", t)
def _blue(t):    return _c("94", t)
def _white(t):   return _c("97", t)

# ── Enhanced animation helpers ────────────────────────────────────────

# ── Animation engine ─────────────────────────────────────────────────
import math

_SPIN = ["◜","◠","◝","◞","◡","◟"]

def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3

def _ease_in_out(t: float) -> float:
    return 3*t*t - 2*t*t*t

def _gradient_bar(pct: float, width: int = 30) -> str:
    """Magenta-themed gradient: dim→blue→magenta→bright-white tip."""
    if _NO_COLOR:
        done = int(width * pct / 100)
        return "[" + "█" * done + "░" * (width - done) + "]"
    cells = []
    filled = width * pct / 100
    for idx in range(width):
        if idx >= filled:
            cells.append(_dim("░"))
        elif idx >= filled - 1:
            cells.append(_c("97", "█"))          # bright-white leading edge
        elif idx / width < 0.40:
            cells.append(_c("35", "▓"))           # dim magenta
        elif idx / width < 0.75:
            cells.append(_c("95", "█"))           # bright magenta
        else:
            cells.append(_c("95;1", "█"))         # vivid magenta tail
    return "[" + "".join(cells) + "]"

def _comet_bar(tick: int, width: int = 30) -> str:
    """Bouncing comet — magenta palette."""
    period = width * 2
    pos    = tick % period
    if pos >= width:
        pos = period - pos
    cells = [_dim("░")] * width
    tail  = [_c("35","▒"), _c("95","▓"), _c("97;1","█"), _c("95","▓"), _c("35","▒")]
    for k, ch in enumerate(tail):
        j = pos - 2 + k
        if 0 <= j < width:
            cells[j] = ch
    return "[" + "".join(cells) + "]"

def _typewrite(line: str, delay: float = 0.018) -> None:
    for ch in line:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def _animate_step(label: str, duration: float = 0.5) -> None:
    steps = 28
    for i in range(steps):
        t     = i / steps
        delay = 0.012 + 0.028 * _ease_in_out(t)
        spin  = _c("95", _SPIN[i % len(_SPIN)])
        trail = _dim("·" * (i % 3 + 1))
        print(f"\r  {spin}  {label}{trail}   ", end="", flush=True)
        time.sleep(delay)
    print(f"\r  {_green('✔')}  {label}   ")

def _animate_bar(label: str, duration: float = 0.7, width: int = 30) -> None:
    fps   = 50
    steps = int(duration * fps)
    for i in range(steps + 1):
        t       = i / steps
        pct     = _ease_out_cubic(t) * 100
        bar     = _gradient_bar(pct, width)
        pct_lbl = _yellow(f"{int(pct):3d}%")
        print(f"\r  {bar} {pct_lbl}  {_dim(label)}", end="", flush=True)
        time.sleep(1 / fps)
    print(f"\r  {_gradient_bar(100, width)} {_green('100%')}  {_bold(label)}  ")

def _animate_scan(label: str, duration: float = 0.65, width: int = 30) -> None:
    fps   = 40
    steps = int(duration * fps)
    for i in range(steps):
        bar = _comet_bar(i, width)
        print(f"\r  {bar}  {_dim(label)}", end="", flush=True)
        time.sleep(1 / fps)
    _animate_bar(label, duration=0.25, width=width)

def _section(title: str, w: int = 52) -> None:
    pad = max(0, w - len(title) - 4)
    l, r = pad // 2, pad - pad // 2
    print(f"\n  {_dim('─' * l)} {_magenta(title)} {_dim('─' * r)}")

def _badge(text: str, color_fn=None) -> str:
    fn = color_fn or _magenta
    return fn(f" {text} ")

_history = []

# ─────────────────────────────────────────────────────────────────────
# AUTO-INSTALL  →  python notify_mcp.py --install
# ─────────────────────────────────────────────────────────────────────
def _auto_install():
    dest     = _CONFIG_DIR / "notify_mcp.py"
    cfg_path = _CONFIG_DIR / "opencode.json"
    username = os.environ.get("USERNAME") or os.environ.get("USER") or "user"

    # ── Header banner ──────────────────────────────────────────────
    w = 56
    print()
    print("  " + _magenta("╔" + "═" * w + "╗"))
    print("  " + _magenta("║") + " " * w + _magenta("║"))
    _typewrite("  " + _magenta("║") + "    🔔  " + _bold(_white("OpenWork  Notify MCP")) + _dim("  ·  Installer v2.0") + " " * 13 + _magenta("║"), delay=0.012)
    print("  " + _magenta("║") + " " * w + _magenta("║"))
    print("  " + _magenta("╚" + "═" * w + "╝"))
    print()

    # ── Step 1 ─────────────────────────────────────────────────────
    _section("SETUP")
    time.sleep(0.08)
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _animate_step(f"Config dir  {_dim(str(_CONFIG_DIR))}")

    # ── Step 2 ─────────────────────────────────────────────────────
    _section("COPY")
    _animate_bar("Copying notify_mcp.py", duration=0.7)
    if _THIS_FILE != dest:
        shutil.copy2(_THIS_FILE, dest)
        print(f"  {_green('✔')}  {_bold('Saved')}  →  {_magenta(str(dest))}")
    else:
        print(f"  {_green('✔')}  Already in place: {_dim(str(dest))}")

    # ── Step 3 ─────────────────────────────────────────────────────
    _section("PATCH  opencode.json")
    time.sleep(0.12)

    new_entry = {
        "type":    "local",
        "command": ["python", f"C:/Users/{username}/.config/opencode/notify_mcp.py"],
        "enabled": True
    }

    if cfg_path.exists():
        try:
            _animate_scan(f"Reading {_dim('opencode.json')}", duration=0.5)
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            bak = cfg_path.with_name("opencode.json.bak")
            shutil.copy2(cfg_path, bak)
            print(f"\n  {_yellow('⚠')}  JSON error — backup → {_dim(str(bak))}")
            print(f"  {_red('→')}  {str(e)}")
            cfg = {}
    else:
        cfg = {}
        print(f"  {_yellow('ℹ')}  opencode.json not found — creating fresh")

    cfg.setdefault("mcp", {})
    force = "--force" in sys.argv

    if "notify" in cfg["mcp"] and not force:
        _animate_step(f"{_badge('notify', _dim)}  already registered — {_yellow('skipped')}", duration=0.25)
        print(f"  {_magenta('ℹ')}  Kept as-is  {_dim('(--force to overwrite)')}")
    else:
        label = f"Force-updating {_badge('notify', _magenta)}" if force else f"Injecting {_badge('notify', _magenta)} entry"
        _animate_step(label, duration=0.35)
        cfg["mcp"]["notify"] = new_entry

    _animate_bar("Writing opencode.json", duration=0.45)
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {_green('✔')}  Saved  →  {_magenta(str(cfg_path))}")

    # ── Footer ─────────────────────────────────────────────────────
    print()
    print("  " + _magenta("┌" + "─" * w + "┐"))
    print("  " + _magenta("│") + f"  {_bold('📦 Optional — better toasts:')}" + " " * (w - 33) + _magenta("│"))
    print("  " + _magenta("│") + f"     {_yellow('pip install winotify')}" + " " * (w - 24) + _magenta("│"))
    print("  " + _magenta("│") + " " * w + _magenta("│"))
    print("  " + _magenta("│") + f"  {_bold('🧪 Test after reload:')}  {_dim('notify_test')}" + " " * (w - 36) + _magenta("│"))
    print("  " + _magenta("│") + f"  {_bold('🔁 Reload OpenWork workspace to activate.')}" + " " * (w - 43) + _magenta("│"))
    print("  " + _magenta("└" + "─" * w + "┘"))
    print()
    _typewrite(f"  {_green(_bold('✅  Done!  notify_mcp is live.'))}  Reload & test.", delay=0.018)
    print()


# ─────────────────────────────────────────────────────────────────────
# TOAST BACKENDS
# ─────────────────────────────────────────────────────────────────────
def _toast_winotify(title, message, duration="short"):
    try:
        from winotify import Notification, audio
        t = Notification(app_id="OpenWork", title=title, msg=message, duration=duration)
        t.set_audio(audio.Default, loop=False)
        t.show(); return True
    except ImportError: return False
    except Exception as ex: _log(f"winotify: {ex}"); return False

def _toast_plyer(title, message):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, app_name="OpenWork", timeout=8)
        return True
    except ImportError: return False
    except Exception as ex: _log(f"plyer: {ex}"); return False

def _toast_win10toast(title, message):
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, message, duration=8, threaded=True)
        return True
    except ImportError: return False
    except Exception as ex: _log(f"win10toast: {ex}"); return False

def _toast_powershell(title, message):
    try:
        import subprocess
        t = title.replace("'","''"); m = message.replace("'","''")
        ps = f"""
$ErrorActionPreference='SilentlyContinue'
try {{
    [Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null
    $xml=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('{t}'))|Out-Null
    $xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{m}'))|Out-Null
    $toast=[Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('OpenWork').Show($toast)
}} catch {{}}
"""
        r = subprocess.run(["powershell","-NoProfile","-NonInteractive","-Command",ps],
                           capture_output=True, timeout=8, check=False)
        return r.returncode == 0
    except Exception as ex: _log(f"powershell: {ex}"); return False

def _toast_print(title, message):
    print(f"\n🔔 [{title}] {message}\n", file=sys.stderr, flush=True); return True

def _toast(title, message, duration="short"):
    for name, fn in [
        ("winotify",   lambda: _toast_winotify(title, message, duration)),
        ("plyer",      lambda: _toast_plyer(title, message)),
        ("win10toast", lambda: _toast_win10toast(title, message)),
        ("powershell", lambda: _toast_powershell(title, message)),
        ("print",      lambda: _toast_print(title, message)),
    ]:
        if fn(): return name
    return "none"

def _record(kind, title, message):
    _history.append({"time":datetime.now().strftime("%H:%M:%S"),"kind":kind,"title":title,"message":message})
    if len(_history) > 50: _history.pop(0)

# ─────────────────────────────────────────────────────────────────────
# TOOL HANDLERS
# ─────────────────────────────────────────────────────────────────────
def _t_notify_done(a):
    task = a.get("task","Task"); message = a.get("message","Completed successfully.")
    title = f"✅ {task} — Done"
    backend = _toast(title, message, "short")
    _record("done", title, message)
    return f"Toast sent via {backend}: [{title}] {message}"

def _t_notify_alert(a):
    message = a.get("message","")
    if not message: return "ERROR: message required"
    title = a.get("title","OpenWork Alert")
    urgent = bool(a.get("urgent",False))
    if not any(title.startswith(e) for e in ("⚠️","🚨","❌","🔴")):
        title = f"{'🚨' if urgent else '⚠️'} {title}"
    backend = _toast(title, message, "long" if urgent else "short")
    _record("alert", title, message)
    return f"Alert sent via {backend}: [{title}] {message}"

def _t_notify_remind(a):
    message = a.get("message","")
    if not message: return "ERROR: message required"
    delay = int(a.get("delay_seconds",60))
    title = a.get("title","🔔 OpenWork Reminder")
    def _fire():
        time.sleep(delay); _toast(title, message, "long")
        _record("reminder_fired", title, message)
    threading.Thread(target=_fire, daemon=True).start()
    t = f"{delay//60}m {delay%60}s" if delay>=60 else f"{delay}s"
    _record("reminder_scheduled", title, f"[in {t}] {message}")
    return f"⏰ Reminder set in {t}: [{title}] {message}"

def _t_notify_progress(a):
    task = a.get("task","Task"); stage = a.get("stage","update")
    step = a.get("step",""); total = a.get("total",""); message = a.get("message","")
    icon = {"start":"🚀","update":"⏳","done":"✅","error":"❌"}.get(stage,"🔄")
    title = f"{icon} {task}"
    if stage=="start":     body = f"Started. {message}" if message else "Starting..."
    elif stage=="done":    body = f"Completed! {message}" if message else "Done."
    elif stage=="error":   body = f"Failed: {message}" if message else "Error."
    else: body = f"Step {step}/{total} — {message}" if (step and total) else (message or "In progress...")
    backend = _toast(title, body, "long" if stage in ("done","error") else "short")
    _record(f"progress:{stage}", title, body)
    return f"Progress ({stage}) via {backend}: [{title}] {body}"

def _t_notify_history(a):
    lim = int(a.get("limit",20))
    if not _history: return "No notifications this session."
    lines = [f"🔔 Last {min(lim,len(_history))} notifications:"]
    for n in reversed(_history[-lim:]):
        lines.append(f"  [{n['time']}] {n['kind']:18s} | {n['title']} — {n['message'][:60]}")
    return "\n".join(lines)

def _t_notify_test(_a):
    backend = _toast("🧪 OpenWork Test", "Notifications are working!", "short")
    _record("test","🧪 OpenWork Test","Notifications are working!")
    status = "✅ Live toast fired!" if backend != "print" else "📋 Headless mode (print fallback)"
    tip = "" if backend != "print" else "\n  → For real toasts: pip install winotify"
    return f"✅ Test sent via [{backend}] — {status}{tip}"

# ─────────────────────────────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────────────────────────────
TOOLS = {
    "notify_done":     (_t_notify_done,     "Send 'task complete' toast. Use after finishing long tasks."),
    "notify_alert":    (_t_notify_alert,    "Send alert/warning toast. urgent=true for longer display."),
    "notify_remind":   (_t_notify_remind,   "Schedule reminder toast after delay_seconds. Non-blocking."),
    "notify_progress": (_t_notify_progress, "Progress toasts: stage=start|update|done|error."),
    "notify_history":  (_t_notify_history,  "List notifications sent this session."),
    "notify_test":     (_t_notify_test,     "Send test toast to verify notification system works."),
}
SCHEMAS = {
    "notify_done":     {"type":"object","properties":{"task":{"type":"string"},"message":{"type":"string"}}},
    "notify_alert":    {"type":"object","properties":{"title":{"type":"string"},"message":{"type":"string"},"urgent":{"type":"boolean"}},"required":["message"]},
    "notify_remind":   {"type":"object","properties":{"message":{"type":"string"},"delay_seconds":{"type":"integer"},"title":{"type":"string"}},"required":["message"]},
    "notify_progress": {"type":"object","properties":{"task":{"type":"string"},"stage":{"type":"string","enum":["start","update","done","error"]},"step":{"type":"string"},"total":{"type":"string"},"message":{"type":"string"}},"required":["task","stage"]},
    "notify_history":  {"type":"object","properties":{"limit":{"type":"integer"}}},
    "notify_test":     {"type":"object","properties":{}},
}

# ─────────────────────────────────────────────────────────────────────
# MCP LOOP
# ─────────────────────────────────────────────────────────────────────
def _handle(req):
    m,rid=req.get("method",""),req.get("id")
    if m=="initialize":
        _send({"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"notify-mcp","version":"2.0.0"}}})
    elif m=="tools/list":
        _send({"jsonrpc":"2.0","id":rid,"result":{"tools":[{"name":n,"description":fd[1],"inputSchema":SCHEMAS[n]} for n,fd in TOOLS.items()]}})
    elif m=="tools/call":
        p=req.get("params",{}); tn,args=p.get("name",""),p.get("arguments",{})
        if tn in TOOLS:
            try: _send({"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":str(TOOLS[tn][0](args))}]}})
            except Exception as ex: _err(rid,str(ex))
        else: _err(rid,f"Tool not found: {tn}")
    elif m=="notifications/initialized": pass
    elif rid is not None: _err(rid,f"Unknown: {m}")

def main():
    _log("🔔 notify-mcp v2.0 started — 6 tools ready")
    mcp_loop("notify", _handle)

if __name__=="__main__":
    if "--install" in sys.argv:
        _auto_install()
    else:
        main()
