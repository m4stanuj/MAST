#!/usr/bin/env python3
"""
setup_mcp.py — OpenWork MCP Setup Wizard v1
============================================
Har MCP ka setup ek jagah se karo.

Usage:
  python setup_mcp.py              → interactive menu (sab MCPs)
  python setup_mcp.py vision       → directly setup vision
  python setup_mcp.py browser      → directly setup browser
  python setup_mcp.py all          → setup all MCPs non-interactively
  python setup_mcp.py status       → sirf status check (kuch install nahi)

MCPs covered:
  memory, research, skills, react, shell, file,
  notify, browser, scrapling, vision, composio
"""

import sys, os, json, subprocess, importlib.util, time, re, shutil, threading
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────
CFG  = Path(os.environ.get("MAST_CONFIG") or os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or ( Path.home() / ".config/opencode"))
OC   = CFG / "opencode.json"
THIS = Path(__file__).resolve()

# ── ANSI colors ─────────────────────────────────────────────────────────
_IS_TTY = sys.stdout.isatty() or os.environ.get("FORCE_COLOR")

def _c(code, t): return f"\033[{code}m{t}\033[0m" if _IS_TTY else t
def bold(t):    return _c("1", t)
def dim(t):     return _c("2", t)
def green(t):   return _c("92", t)
def yellow(t):  return _c("93", t)
def red(t):     return _c("91", t)
def cyan(t):    return _c("96", t)
def magenta(t): return _c("95", t)
def blue(t):    return _c("94", t)
def white(t):   return _c("97", t)

OK  = green("✓")
ERR = red("✗")
WRN = yellow("⚠")
DOT = dim("·")

def hline(char="─", width=60): return dim(char * width)
def header(title):
    w = 60
    print()
    print(magenta("┌" + "─"*(w-2) + "┐"))
    pad = (w - 2 - len(title)) // 2
    print(magenta("│") + " "*pad + bold(white(title)) + " "*(w-2-pad-len(title)) + magenta("│"))
    print(magenta("└" + "─"*(w-2) + "┘"))
    print()

def section(title):
    print()
    print(cyan("  ── ") + bold(title) + cyan(" " + "─"*(50-len(title))))

def info(msg):  print(f"  {cyan('→')} {msg}")
def ok(msg):    print(f"  {OK} {green(msg)}")
def warn(msg):  print(f"  {WRN} {yellow(msg)}")
def err(msg):   print(f"  {ERR} {red(msg)}")
def step(msg):  print(f"  {DOT} {dim(msg)}")

# ── Spinner ──────────────────────────────────────────────────────────────
def _spinner(msg, done_event):
    frames = ["◜","◠","◝","◞","◡","◟"]
    i = 0
    while not done_event.is_set():
        if _IS_TTY:
            sys.stdout.write(f"\r  {magenta(frames[i%len(frames)])} {msg} ")
            sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    if _IS_TTY:
        sys.stdout.write("\r" + " "*60 + "\r")
        sys.stdout.flush()

def run_with_spinner(msg, fn):
    ev = threading.Event()
    t = threading.Thread(target=_spinner, args=(msg, ev), daemon=True)
    t.start()
    try:
        result = fn()
    finally:
        ev.set()
        t.join()
    return result

# ── pip helpers ───────────────────────────────────────────────────────────
def _pkg_installed(import_name: str) -> bool:
    mod_map = {
        "PIL": "PIL",
        "browser_use": "browser_use",
        "composio_core": "composio",
        "cv2": "cv2",
        "scrapling": "scrapling",
        "mss": "mss",
    }
    name = mod_map.get(import_name, import_name)
    return importlib.util.find_spec(name) is not None

def _pip_install(packages: list[str], extra: list[str] = None) -> tuple[bool, str]:
    cmd = [sys.executable, "-m", "pip", "install", "--quiet"] + packages
    if extra:
        cmd += extra
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode == 0:
            return True, ""
        return False, (r.stderr or r.stdout).strip()[-400:]
    except subprocess.TimeoutExpired:
        return False, "Timed out (180s)"
    except Exception as e:
        return False, str(e)

def _run_cmd(cmd: list[str], timeout=120) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)

# ── opencode.json helpers ─────────────────────────────────────────────────
def _load_oc() -> dict:
    try:
        if OC.exists():
            return json.loads(OC.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_oc(data: dict):
    CFG.mkdir(parents=True, exist_ok=True)
    tmp = OC.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(OC)

def _set_mcp_env(mcp_name: str, key: str, value: str):
    data = _load_oc()
    data.setdefault("mcp", {}).setdefault(mcp_name, {}).setdefault("env", {})[key] = value
    _save_oc(data)

def _get_mcp_env(mcp_name: str, key: str) -> str:
    data = _load_oc()
    return data.get("mcp", {}).get(mcp_name, {}).get("env", {}).get(key, "")

def _ask(prompt: str, default: str = "") -> str:
    hint = f" [{dim(default)}]" if default else ""
    try:
        val = input(f"  {cyan('?')} {prompt}{hint}: ").strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)

def _confirm(msg: str, default=True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    try:
        val = input(f"  {cyan('?')} {msg} {dim(hint)}: ").strip().lower()
        if not val:
            return default
        return val.startswith("y")
    except (KeyboardInterrupt, EOFError):
        print()
        return False

# ═══════════════════════════════════════════════════════════════════════
# MCP SETUP DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

def _check_dep(import_name):
    return OK if _pkg_installed(import_name) else ERR

# ─────────────────────────────────
# 1. MEMORY
# ─────────────────────────────────
def setup_memory():
    header("MEMORY MCP SETUP")
    print(f"  3-Tier memory: Core + Recall + ChromaDB (archival vector search)")
    print()

    section("Dependency Check")
    chroma_ok = _pkg_installed("chromadb")
    print(f"  {_check_dep('chromadb')} chromadb  {dim('(optional — semantic search)')}")

    if not chroma_ok:
        warn("ChromaDB nahi hai — keyword search use hoga (works fine)")
        if _confirm("ChromaDB install karein? (better archival search)"):
            def _inst():
                return _pip_install(["chromadb"])
            ok_, msg = run_with_spinner("Installing chromadb...", _inst)
            if ok_:
                ok("chromadb installed!")
            else:
                err(f"Install failed: {msg}")
                warn("Keyword search fallback use hoga — kaam chalega")
    else:
        ok("chromadb already installed")

    section("Status")
    mem_file = CFG / "memory_3tier.json"
    if mem_file.exists():
        try:
            data = json.loads(mem_file.read_text(encoding="utf-8"))
            facts = len(data.get("core", {}).get("important_facts", []))
            tasks = len(data.get("recall", {}).get("recent_tasks", []))
            ok(f"Memory file found — {facts} facts, {tasks} recent tasks")
        except Exception:
            warn("Memory file exists but unreadable — will reset on first use")
    else:
        info("Memory file nahi hai — first use pe auto-create hoga")

    print()
    ok("Memory MCP ready!")

# ─────────────────────────────────
# 2. RESEARCH
# ─────────────────────────────────
def setup_research():
    header("RESEARCH MCP SETUP")
    print(f"  Web research, DuckDuckGo search, Wikipedia, URL fetch")
    print()

    section("Dependency Check")
    req_ok = _pkg_installed("requests")
    print(f"  {_check_dep('requests')} requests")

    if not req_ok:
        info("Installing requests...")
        ok_, msg = _pip_install(["requests"])
        if ok_:
            ok("requests installed!")
        else:
            err(f"Failed: {msg}")
    else:
        ok("requests already installed")

    section("Quick Test")
    try:
        import requests
        r = requests.get("https://duckduckgo.com", timeout=5)
        ok(f"DuckDuckGo reachable ({r.status_code})")
    except Exception as e:
        warn(f"Network check failed: {e}")

    print()
    ok("Research MCP ready!")

# ─────────────────────────────────
# 3. SKILLS / REACT / SHELL
# ─────────────────────────────────
def setup_skills():
    header("SKILLS MCP SETUP")
    print(f"  Skill library — no external deps needed")
    print()
    section("Status")

    skills_dir = CFG / "skills"
    if skills_dir.exists():
        count = len(list(skills_dir.glob("*.md"))) + len(list(skills_dir.glob("*.json")))
        ok(f"Skills dir exists ({count} files)")
    else:
        info("Skills dir nahi hai — auto-create hoga on first use")

    ok("Skills MCP ready — no setup needed!")

def setup_react():
    header("REACT MCP SETUP")
    print(f"  React component generator — no external deps")
    print()
    ok("React MCP ready — no setup needed!")

def setup_shell():
    header("SHELL MCP SETUP")
    print(f"  Shell command executor — no external deps")
    print()
    warn("Shell MCP powerful hai — sirf trusted environments mein use karo")
    ok("Shell MCP ready — no setup needed!")

# ─────────────────────────────────
# 4. FILE
# ─────────────────────────────────
def setup_file():
    header("FILE MCP SETUP")
    print(f"  File read/write/search, archives, images, Office docs")
    print()

    OPTIONAL_DEPS = [
        ("pypdf",        "pypdf",        "PDF text extraction"),
        ("docx",         "python-docx",  "Word .docx read/write"),
        ("openpyxl",     "openpyxl",     "Excel .xlsx read"),
        ("pptx",         "python-pptx",  "PowerPoint .pptx read"),
        ("PIL",          "Pillow",        "Image info & processing"),
        ("py7zr",        "py7zr",         "7z archive support"),
    ]

    section("Dependency Check")
    missing = []
    for import_name, pkg, desc in OPTIONAL_DEPS:
        ok_ = _pkg_installed(import_name)
        status = OK if ok_ else yellow("○")
        print(f"  {status} {pkg:<18} {dim(desc)}")
        if not ok_:
            missing.append((import_name, pkg, desc))

    if not missing:
        ok("All optional deps installed!")
    else:
        print()
        warn(f"{len(missing)} optional packages missing")
        print(f"  {dim('(File MCP works without them, but limited functionality)')}")
        print()
        if _confirm("Saare missing packages install karein?"):
            pkgs = [pkg for _, pkg, _ in missing]
            def _inst():
                return _pip_install(pkgs)
            ok_, msg = run_with_spinner(f"Installing {', '.join(pkgs)}...", _inst)
            if ok_:
                ok("All installed!")
            else:
                err(f"Some failed: {msg}")
                info("Individual install: pip install <package>")

    print()
    ok("File MCP ready!")

# ─────────────────────────────────
# 5. NOTIFY
# ─────────────────────────────────
def setup_notify():
    header("NOTIFY MCP SETUP")
    print(f"  Windows toast notifications with animation")
    print()
    print(f"  {dim('Backend priority: winotify > plyer > win10toast > PowerShell > print')}")
    print()

    section("Backend Check")
    backends = [
        ("winotify",   "winotify",   "Best — native Win10/11 toasts"),
        ("plyer",      "plyer",       "Cross-platform fallback"),
        ("win10toast", "win10toast", "Legacy fallback"),
    ]

    found_any = False
    missing = []
    for import_name, pkg, desc in backends:
        ok_ = _pkg_installed(import_name)
        status = OK if ok_ else yellow("○")
        print(f"  {status} {pkg:<14} {dim(desc)}")
        if ok_:
            found_any = True
        else:
            missing.append(pkg)

    print()
    if found_any:
        ok("At least one notification backend available!")
    else:
        warn("Koi backend nahi — PowerShell fallback use hoga (works, no pip needed)")

    if not found_any or ("winotify" in missing and _confirm("winotify install karein? (best quality)", default=True)):
        def _inst():
            return _pip_install(["winotify"])
        ok_, msg = run_with_spinner("Installing winotify...", _inst)
        if ok_:
            ok("winotify installed — best toast notifications!")
        else:
            err(f"Failed: {msg}")
            info("PowerShell fallback will be used")

    print()
    ok("Notify MCP ready!")

# ─────────────────────────────────
# 6. BROWSER
# ─────────────────────────────────
def setup_browser():
    header("BROWSER MCP SETUP")
    print(f"  AI browser agent — navigate, click, fill forms, extract data")
    print()
    print(f"  {dim('Uses browser_use library + Playwright Chromium')}")
    print()

    section("Dependency Check")
    bu_ok  = _pkg_installed("browser_use")
    pw_ok  = _pkg_installed("playwright")

    print(f"  {_check_dep('browser_use')} browser-use")
    print(f"  {_check_dep('playwright')} playwright")

    # Check if chromium is installed
    chromium_ok = False
    try:
        r = subprocess.run(
            [sys.executable, "-c", "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop()"],
            capture_output=True, timeout=15
        )
        chromium_ok = r.returncode == 0
    except Exception:
        pass
    print(f"  {'✓' if chromium_ok else '✗'} chromium browser {'(installed)' if chromium_ok else '(not installed)'}")
    print()

    if not bu_ok:
        info("browser-use + playwright install karna padega")
        if not _confirm("Install karein?"):
            warn("Browser MCP skip kiya")
            return

        def _inst():
            return _pip_install(["browser-use", "playwright"])
        ok_, msg = run_with_spinner("Installing browser-use & playwright...", _inst)
        if not ok_:
            err(f"pip install failed: {msg}")
            return
        ok("Packages installed!")
        bu_ok = True

    if bu_ok and not chromium_ok:
        info("Chromium browser download karna hai (~150MB one-time)")
        if _confirm("playwright install chromium chalayein?"):
            def _inst():
                return _run_cmd([sys.executable, "-m", "playwright", "install", "chromium"], timeout=300)
            ok_, msg = run_with_spinner("Downloading Chromium (may take 1-2 min)...", _inst)
            if ok_:
                ok("Chromium installed!")
            else:
                err(f"Failed: {msg}")
                info("Manual: python -m playwright install chromium")
    elif chromium_ok:
        ok("Chromium already installed!")

    section("Timeout Config")
    cur = _get_mcp_env("browser-use", "BROWSER_TIMEOUT") or "120"
    print(f"  Current timeout: {cyan(cur)}s")
    new_timeout = _ask("Timeout seconds (complex tasks ke liye badha sakte ho)", default=cur)
    if new_timeout != cur:
        _set_mcp_env("browser-use", "BROWSER_TIMEOUT", new_timeout)
        ok(f"Timeout set to {new_timeout}s in opencode.json")

    print()
    ok("Browser MCP ready!")

# ─────────────────────────────────
# 7. SCRAPLING
# ─────────────────────────────────
def setup_scrapling():
    header("SCRAPLING MCP SETUP")
    print(f"  Anti-bot web scraper — bypasses Cloudflare, extracts clean text")
    print()

    section("Dependency Check")
    sc_ok = _pkg_installed("scrapling")
    print(f"  {_check_dep('scrapling')} scrapling")
    print()

    if not sc_ok:
        if _confirm("scrapling install karein?"):
            def _inst():
                return _pip_install(["scrapling"])
            ok_, msg = run_with_spinner("Installing scrapling...", _inst)
            if ok_:
                ok("scrapling installed!")
                # Scrapling needs playwright too
                pw_ok = _pkg_installed("playwright")
                if not pw_ok:
                    info("scrapling playwright bhi chahiye")
                    _pip_install(["playwright"])
                    _run_cmd([sys.executable, "-m", "playwright", "install", "chromium"], timeout=300)
            else:
                err(f"Failed: {msg}")
    else:
        ok("scrapling already installed!")

    section("Quick Test")
    if _pkg_installed("scrapling"):
        if _confirm("Quick scrape test karein? (example.com)"):
            try:
                def _test():
                    from scrapling.defaults import Fetcher
                    f = Fetcher(auto_match=True)
                    p = f.get("https://example.com", timeout=15)
                    return p.get_all_text()
                result = run_with_spinner("Testing scrape...", _test)
                if result and len(result) > 50:
                    ok(f"Scrape works! ({len(result)} chars from example.com)")
                else:
                    warn("Scrape returned minimal content")
            except Exception as e:
                warn(f"Test failed: {e}")

    print()
    ok("Scrapling MCP ready!")

# ─────────────────────────────────
# 8. VISION
# ─────────────────────────────────
def setup_vision():
    header("VISION MCP SETUP")
    print(f"  Screenshot + Vision AI — llama-server backend (local GGUF)")
    print()
    print(f"  {dim('Backend: llama-server (llama.cpp) — NOT Ollama')}")
    print(f"  {dim('Models:  Qwen3-VL 7B, LLaVA, InternVL, Moondream, etc.')}")
    print()

    # ── Step 1: Python deps
    section("Step 1/4 — Python Dependencies")
    deps = [
        ("mss",       "mss",       "Fast screenshot"),
        ("PIL",       "Pillow",    "Image processing"),
        ("pyautogui", "pyautogui", "Mouse/keyboard control"),
    ]
    missing_deps = []
    for import_name, pkg, desc in deps:
        ok_ = _pkg_installed(import_name)
        print(f"  {OK if ok_ else ERR} {pkg:<14} {dim(desc)}")
        if not ok_:
            missing_deps.append(pkg)

    if missing_deps:
        print()
        if _confirm(f"Install missing: {', '.join(missing_deps)}?"):
            def _inst():
                return _pip_install(missing_deps)
            ok_, msg = run_with_spinner("Installing...", _inst)
            if ok_:
                ok("Python deps installed!")
            else:
                err(f"Failed: {msg}")
    else:
        print()
        ok("All Python deps installed!")

    # ── Step 2: llama-server
    section("Step 2/4 — llama-server Binary")

    # Check common install locations
    llama_paths = [
        CFG / "llama-server.exe",
        CFG / "llama-server",
        Path.home() / "llama-server.exe",
        Path("C:/llama/llama-server.exe"),
        Path(os.path.expanduser("~/llama-server.exe")),
    ]
    # Also check PATH
    llama_in_path = shutil.which("llama-server") or shutil.which("llama-server.exe")
    if llama_in_path:
        llama_paths.insert(0, Path(llama_in_path))

    found_llama = next((p for p in llama_paths if p.exists()), None)

    if found_llama:
        ok(f"llama-server found: {cyan(str(found_llama))}")
        # Write path to opencode.json env
        _set_mcp_env("vision-qwen", "LLAMA_EXE", str(found_llama))
    else:
        warn("llama-server nahi mila PATH ya config dir mein")
        print()
        print(f"  {bold('Download karo:')} {cyan('https://github.com/ggerganov/llama.cpp/releases')}")
        print(f"  {dim('Releases → latest → Windows → llama-server.exe ya llama-b*.zip')}")
        print()
        llama_manual = _ask("llama-server.exe ka path enter karo (ya Enter to skip)")
        if llama_manual and Path(llama_manual).exists():
            _set_mcp_env("vision-qwen", "LLAMA_EXE", llama_manual)
            ok(f"Path saved!")
        else:
            warn("llama-server path set nahi hua — vision text-only fallback mode mein chalega")

    # ── Step 3: GGUF Model
    section("Step 3/4 — Vision Model (GGUF)")

    # Common model locations
    model_dirs = [
        CFG / "models",
        Path("C:/models"),
        Path.home() / "models",
        Path.home() / "llama" / "models",
    ]

    found_models = []
    for mdir in model_dirs:
        if mdir.exists():
            found_models.extend(list(mdir.glob("*vl*.gguf")) + list(mdir.glob("*llava*.gguf")) + list(mdir.glob("*vision*.gguf")) + list(mdir.glob("*qwen*vl*.gguf")))

    if found_models:
        ok(f"Vision GGUF models found:")
        for m in found_models[:5]:
            size_mb = m.stat().st_size // (1024*1024)
            print(f"    {cyan('►')} {m.name} {dim(f'({size_mb} MB)')}")
        selected = str(found_models[0])
        if len(found_models) > 1:
            print()
            selected = _ask(f"Model path (default: {found_models[0].name})", default=str(found_models[0]))
    else:
        warn("Koi vision GGUF model nahi mila")
        print()
        print(f"  {bold('Recommended models:')}")
        print(f"    {cyan('►')} Qwen3-VL-7B-Instruct-Q4_K_M.gguf   {dim('(best, 4.5GB)')}")
        print(f"    {cyan('►')} qwen2.5-vl-7b-instruct-q4_k_m.gguf  {dim('(stable, 4.5GB)')}")
        print(f"    {cyan('►')} moondream2.gguf                       {dim('(tiny, 1.7GB, fast)')}")
        print()
        print(f"  {dim('Download from: https://huggingface.co/bartowski')}")
        print()
        selected = _ask("GGUF model path enter karo (ya Enter to skip)", default="")

    mmproj_path = ""
    if selected and Path(selected).exists():
        _set_mcp_env("vision-qwen", "VISION_MODEL_PATH", selected)
        ok(f"Model path saved: {Path(selected).name}")

        # Find mmproj
        model_dir = Path(selected).parent
        mmproj_files = list(model_dir.glob("*mmproj*.gguf"))
        if mmproj_files:
            mmproj_path = str(mmproj_files[0])
            ok(f"mmproj found: {mmproj_files[0].name}")
        else:
            warn("mmproj file nahi mila — vision ke liye zaruri hai!")
            print(f"  {dim('mmproj = multimodal projector, model ke saath aata hai HuggingFace pe')}")
            mmproj_path = _ask("mmproj .gguf path enter karo (ya Enter to skip)", default="")
            if mmproj_path and Path(mmproj_path).exists():
                ok("mmproj path saved!")

    # ── Step 4: Launch script + Config
    section("Step 4/4 — Launch Script & Config")

    cur_url = _get_mcp_env("vision-qwen", "LLAMA_URL") or "http://localhost:8080"
    cur_port = cur_url.split(":")[-1].replace("/","") or "8080"
    cur_w    = _get_mcp_env("vision-qwen", "SCREEN_W") or "1920"
    cur_h    = _get_mcp_env("vision-qwen", "SCREEN_H") or "1080"
    cur_gpu  = _ask("GPU layers (0=CPU only, 35=full GPU, -1=auto)", default="35")

    print()
    print(f"  Screen resolution: {cur_w}x{cur_h}")
    new_w = _ask("Screen width", default=cur_w)
    new_h = _ask("Screen height", default=cur_h)

    _set_mcp_env("vision-qwen", "LLAMA_URL", f"http://localhost:{cur_port}")
    _set_mcp_env("vision-qwen", "SCREEN_W", new_w)
    _set_mcp_env("vision-qwen", "SCREEN_H", new_h)

    # Generate start_vision.bat
    if selected and Path(selected).exists():
        llama_exe = _get_mcp_env("vision-qwen", "LLAMA_EXE") or "llama-server"
        bat_lines = [
            "@echo off",
            f"rem OpenWork — Vision MCP llama-server launcher",
            f"rem Auto-generated by setup_mcp.py",
            "",
            f'set MODEL={selected}',
            f'set MMPROJ={mmproj_path}',
            f'set PORT={cur_port}',
            f'set GPU_LAYERS={cur_gpu}',
            "",
            "echo Starting llama-server for Vision MCP...",
            f'"{llama_exe}" ^',
            f'  --model %MODEL% ^',
        ]
        if mmproj_path:
            bat_lines.append(f'  --mmproj %MMPROJ% ^')
        bat_lines += [
            f'  --port %PORT% ^',
            f'  --n-gpu-layers %GPU_LAYERS% ^',
            f'  --ctx-size 4096 ^',
            f'  --host 0.0.0.0',
            "",
            "pause",
        ]
        bat_path = CFG / "start_vision.bat"
        bat_path.write_text("\n".join(bat_lines), encoding="utf-8")
        ok(f"Launch script: {cyan(str(bat_path))}")
        info("Run start_vision.bat BEFORE using vision MCP")
    else:
        info("Model path set nahi hai — start_vision.bat nahi bana")
        info("Manual launch: llama-server --model <path> --mmproj <path> --port 8080 --n-gpu-layers 35")

    print()
    ok("Vision MCP configured!")

# ─────────────────────────────────
# 9. COMPOSIO
# ─────────────────────────────────
def setup_composio():
    header("COMPOSIO MCP SETUP")
    print(f"  300+ app integrations — Gmail, GitHub, Notion, Slack, etc.")
    print()
    print(f"  {dim('Free tier: composio.dev — 10k actions/month')}")
    print()

    # ── Step 1: Package
    section("Step 1/3 — Package")
    cc_ok = _pkg_installed("composio_core")
    print(f"  {_check_dep('composio_core')} composio-core")

    if not cc_ok:
        if _confirm("pip install composio-core?"):
            def _inst():
                return _pip_install(["composio-core"])
            ok_, msg = run_with_spinner("Installing...", _inst)
            if ok_:
                ok("composio-core installed!")
            else:
                err(f"Failed: {msg}")
                return
    else:
        ok("composio-core already installed!")

    # ── Step 2: API Key
    section("Step 2/3 — API Key")
    print(f"  Get free key from: {cyan('https://app.composio.dev/settings')}")
    print()

    data = _load_oc()
    cur_key = data.get("mcp", {}).get("composio", {}).get("env", {}).get("COMPOSIO_API_KEY", "")
    if cur_key and not cur_key.startswith("REPLACE"):
        ok(f"API key already set: {dim(cur_key[:8]+'...')}")
        if not _confirm("Change karna hai?", default=False):
            pass
        else:
            cur_key = ""

    if not cur_key or cur_key.startswith("REPLACE"):
        new_key = _ask("COMPOSIO_API_KEY paste karo")
        if new_key and len(new_key) > 10:
            _set_mcp_env("composio", "COMPOSIO_API_KEY", new_key)
            ok("API key saved in opencode.json!")
        else:
            warn("Key set nahi hua — composio MCP kaam nahi karega")
            return

    # ── Step 3: App Auth
    section("Step 3/3 — App Authentication")
    print(f"  {dim('Common apps: gmail, github, notion, slack, calendar, drive')}")
    print()

    apps_to_auth = _ask("Kaun se apps authenticate karein? (comma-separated, ya Enter to skip)", default="")
    if apps_to_auth.strip():
        apps = [a.strip() for a in apps_to_auth.split(",") if a.strip()]
        for app in apps:
            info(f"Authenticating {app}...")
            ok_, msg = _run_cmd(
                [sys.executable, str(CFG / "composio_mcp.py"), "--auth", app],
                timeout=120
            )
            if ok_:
                ok(f"{app} authenticated!")
            else:
                warn(f"{app} auth failed or needs browser: {msg[:100]}")
                info(f"Manual: composio add {app}")

    print()
    ok("Composio MCP configured!")

# ═══════════════════════════════════════════════════════════════════════
# STATUS CHECK (no installs)
# ═══════════════════════════════════════════════════════════════════════

MCP_DEF = {
    "memory":    {"deps": ["chromadb"],                        "optional": True,  "label": "3-Tier Memory"},
    "research":  {"deps": ["requests"],                        "optional": False, "label": "Deep Research"},
    "skills":    {"deps": [],                                  "optional": False, "label": "Skills Library"},
    "react":     {"deps": [],                                  "optional": False, "label": "React Generator"},
    "shell":     {"deps": [],                                  "optional": False, "label": "Shell Execute"},
    "file":      {"deps": ["pypdf","docx","PIL","openpyxl"],   "optional": True,  "label": "File Operations"},
    "notify":    {"deps": ["winotify"],                        "optional": True,  "label": "Notifications"},
    "browser":   {"deps": ["browser_use","playwright"],        "optional": False, "label": "Browser Agent"},
    "scrapling": {"deps": ["scrapling"],                       "optional": False, "label": "Anti-Bot Scraper"},
    "vision":    {"deps": ["mss","PIL","pyautogui"],           "optional": False, "label": "Vision AI"},
    "composio":  {"deps": ["composio_core"],                   "optional": False, "label": "App Integrations"},
}

def show_status():
    header("OPENWORK MCP STATUS")

    oc = _load_oc()
    mcp_cfg = oc.get("mcp", {})

    # Widths
    rows = []
    for name, d in MCP_DEF.items():
        cfg_entry = mcp_cfg.get(name, {})
        enabled = cfg_entry.get("enabled", True)

        dep_results = []
        for dep in d["deps"]:
            dep_results.append((dep, _pkg_installed(dep)))

        all_ok    = all(ok_ for _, ok_ in dep_results)
        some_ok   = any(ok_ for _, ok_ in dep_results) if dep_results else True
        no_deps   = len(dep_results) == 0

        if no_deps:
            health = green("● READY")
        elif all_ok:
            health = green("● READY")
        elif d["optional"] and some_ok:
            health = yellow("◑ PARTIAL")
        elif d["optional"] and not some_ok:
            health = yellow("○ OPTIONAL")
        else:
            health = red("○ NEEDS SETUP")

        if not enabled:
            health = dim("  DISABLED")

        rows.append((name, d["label"], health, dep_results, d["optional"]))

    # Print table
    print(f"  {'MCP':<12} {'Label':<22} {'Status':<20} {'Deps'}")
    print(f"  {dim('─'*12)} {dim('─'*22)} {dim('─'*20)} {dim('─'*20)}")
    for name, label, health, deps, optional in rows:
        dep_str = ""
        if deps:
            parts = []
            for d, ok_ in deps:
                parts.append(f"{green(d) if ok_ else red(d)}")
            dep_str = ", ".join(parts)
        else:
            dep_str = dim("none")
        spacing = " " * max(0, 12 - len(name))
        print(f"  {cyan(name)}{spacing}  {label:<22} {health}  {dep_str}")

    print()

    # Env vars check
    section("opencode.json")
    if OC.exists():
        ok(f"Found: {cyan(str(OC))}")
    else:
        err(f"NOT FOUND: {str(OC)}")
        info("Run install.ps1 to create it")

    # Vision extra status
    llama_url = _get_mcp_env("vision-qwen", "LLAMA_URL") or "http://localhost:8080"
    try:
        import urllib.request
        urllib.request.urlopen(f"{llama_url}/health", timeout=2)
        ok(f"llama-server ONLINE at {llama_url}")
    except Exception:
        warn(f"llama-server OFFLINE ({llama_url}) — vision text-only mode")

    # Composio key check
    cc_key = _get_mcp_env("composio", "COMPOSIO_API_KEY") or ""
    if cc_key and not cc_key.startswith("REPLACE"):
        ok(f"Composio API key set ({cc_key[:8]}...)")
    else:
        warn("Composio API key NOT set")

    print()

# ═══════════════════════════════════════════════════════════════════════
# MAIN MENU
# ═══════════════════════════════════════════════════════════════════════

SETUP_FNS = {
    "memory":    setup_memory,
    "research":  setup_research,
    "skills":    setup_skills,
    "react":     setup_react,
    "shell":     setup_shell,
    "file":      setup_file,
    "notify":    setup_notify,
    "browser":   setup_browser,
    "scrapling": setup_scrapling,
    "vision":    setup_vision,
    "composio":  setup_composio,
}

MENU_ITEMS = [
    ("1",  "memory",    "3-Tier Memory",      "chromadb optional"),
    ("2",  "research",  "Deep Research",      "requests"),
    ("3",  "skills",    "Skills Library",     "no deps"),
    ("4",  "react",     "React Generator",    "no deps"),
    ("5",  "shell",     "Shell Execute",      "no deps"),
    ("6",  "file",      "File Operations",    "pypdf/docx/PIL optional"),
    ("7",  "notify",    "Notifications",      "winotify optional"),
    ("8",  "browser",   "Browser Agent",      "browser-use + playwright"),
    ("9",  "scrapling", "Anti-Bot Scraper",   "scrapling"),
    ("10", "vision",    "Vision AI",          "mss + Pillow + llama-server"),
    ("11", "composio",  "App Integrations",   "composio-core + API key"),
]

def main_menu():
    header("OPENWORK MCP SETUP WIZARD")
    print(f"  Config dir: {cyan(str(CFG))}")
    print()

    # Quick status bar
    ready = sum(1 for _, name, _, _ in MENU_ITEMS
                if all(_pkg_installed(d) for d in MCP_DEF.get(name, {}).get("deps", [])
                       if not MCP_DEF.get(name, {}).get("optional", False))
                or not MCP_DEF.get(name, {}).get("deps"))
    total = len(MENU_ITEMS)
    bar_w = 30
    filled = int(bar_w * ready / total)
    bar = green("█" * filled) + dim("░" * (bar_w - filled))
    print(f"  [{bar}] {green(str(ready))}/{total} MCPs ready")
    print()

    print(f"  {'#':<4} {'MCP':<12} {'Name':<22} {dim('Requires')}")
    print(f"  {dim('─'*4)} {dim('─'*12)} {dim('─'*22)} {dim('─'*24)}")
    for num, name, label, requires in MENU_ITEMS:
        deps = MCP_DEF.get(name, {}).get("deps", [])
        all_ok = all(_pkg_installed(d) for d in deps) if deps else True
        status = green("●") if all_ok else yellow("○")
        spacing = " " * max(0, 12 - len(name))
        print(f"  {dim(num):<4} {status} {cyan(name)}{spacing}  {label:<22} {dim(requires)}")

    print()
    print(f"  {dim('0')}  {dim('Status check (kuch install nahi)')}")
    print(f"  {dim('a')}  {bold('ALL setup karo')} {dim('(ek ek karke sab)')}")
    print(f"  {dim('q')}  {dim('Quit')}")
    print()

    choice = _ask("Setup karna hai kaunsa? (number/name/all/status)").strip().lower()

    if choice in ("q", "quit", "exit"):
        print(f"\n  {dim('Bye!')}\n")
        sys.exit(0)

    elif choice in ("0", "status"):
        show_status()

    elif choice in ("a", "all"):
        if _confirm("Saare MCPs setup karo?"):
            for _, name, label, _ in MENU_ITEMS:
                print()
                print(magenta(f"  ═══ {label} ═══"))
                SETUP_FNS[name]()
        ok("All MCPs setup done!")

    elif choice.isdigit() and 1 <= int(choice) <= len(MENU_ITEMS):
        idx = int(choice) - 1
        _, name, _, _ = MENU_ITEMS[idx]
        SETUP_FNS[name]()

    elif choice in SETUP_FNS:
        SETUP_FNS[choice]()

    else:
        warn(f"Invalid choice: {choice!r}")

    print()
    if _confirm("Koi aur MCP setup karna hai?", default=False):
        main_menu()


def main():
    # Ensure config dir exists
    CFG.mkdir(parents=True, exist_ok=True)

    args = sys.argv[1:]

    if not args:
        main_menu()
        return

    cmd = args[0].lower().strip()

    if cmd == "status":
        show_status()
    elif cmd == "all":
        for _, name, label, _ in MENU_ITEMS:
            print()
            print(magenta(f"  ═══ {label} ═══"))
            SETUP_FNS[name]()
        print()
        ok("All MCPs setup complete!")
    elif cmd in SETUP_FNS:
        SETUP_FNS[cmd]()
    else:
        err(f"Unknown MCP: {cmd!r}")
        print(f"  Available: {', '.join(SETUP_FNS.keys())}")
        print(f"  Usage: python setup_mcp.py [mcp_name | all | status]")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {dim('Interrupted. Bye!')}\n")
        sys.exit(0)
