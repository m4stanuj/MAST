#!/usr/bin/env python3
"""
mcp_doctor.py — OpenWork v8 Health Checker
===========================================
Run anytime to diagnose why an MCP is Offline.

Usage:
  python mcp_doctor.py           — full check, human-readable
  python mcp_doctor.py --fix     — auto-fix opencode.json format issues
  python mcp_doctor.py --watch   — re-check every 15s (live monitor)
  python mcp_doctor.py --json    — machine-readable JSON output
  python mcp_doctor.py --test    — send real MCP initialize ping to each server
"""
import sys, os, json, subprocess, importlib.util, time, re
from pathlib import Path

CFG = Path(os.environ.get("MAST_CONFIG") or os.environ.get("OPENWORK_CONFIG") or ( Path.home() / ".config/opencode"))
OC  = CFG / "opencode.json"

# ── MCP definitions ───────────────────────────────────────────────────
MCPS = {
    "memory":      {"file":"memory_mcp.py",      "deps":[],                            "critical":True,  "async":False},
    "research":    {"file":"research_mcp.py",     "deps":["requests"],                  "critical":False, "async":False},
    "skills":      {"file":"skills_mcp.py",       "deps":[],                            "critical":False, "async":False},
    "react":       {"file":"react_mcp.py",        "deps":[],                            "critical":False, "async":False},
    "browser-use": {"file":"browser_mcp.py",      "deps":["browser_use","playwright"],  "critical":False, "async":True},
    "scrapling":   {"file":"scrapling_mcp.py",    "deps":["scrapling"],                 "critical":False, "async":True},
    "vision-qwen": {"file":"vision_mcp.py",       "deps":["mss","PIL"],                 "critical":False, "async":True},
    "file":        {"file":"file_mcp.py",         "deps":[],                            "critical":True,  "async":False},
    "notify":      {"file":"notify_mcp.py",       "deps":[],                            "critical":False, "async":False},
    "shell":       {"file":"shell_mcp.py",        "deps":[],                            "critical":False, "async":False},
    "composio":    {"file":"composio_mcp.py",     "deps":["composio_core"],             "critical":False, "async":False},
    "firecrawl":   {"file":None,                   "deps":["node"],                      "critical":False, "async":True},
}

DEP_FIX = {
    "requests":      "pip install requests",
    "browser_use":   "pip install browser-use",
    "playwright":    "playwright install chromium",
    "scrapling":     "pip install scrapling",
    "PIL":           "pip install Pillow",
    "mss":           "pip install mss",
    "composio_core": "pip install composio-core",
    "chromadb":      "pip install chromadb  (optional — improves memory search)",
    "node":          "Install Node.js LTS from https://nodejs.org",
}

INIT_MSG = json.dumps({
    "jsonrpc":"2.0","id":1,"method":"initialize",
    "params":{"protocolVersion":"2024-11-05","capabilities":{},
              "clientInfo":{"name":"mcp_doctor","version":"1.0"}}
})

# ── Checks ────────────────────────────────────────────────────────────
def chk_python():
    try:
        r = subprocess.run(["python","--version"], capture_output=True, text=True, timeout=5)
        v = (r.stdout+r.stderr).strip()
        major = int(v.split()[1].split(".")[0]) if v else 0
        minor = int(v.split()[1].split(".")[1]) if v else 0
        ok = major==3 and minor>=9
        return {"ok":ok,"version":v,"note":"" if ok else "Python 3.9+ required"}
    except Exception as e:
        return {"ok":False,"version":"not found","note":str(e)}

def chk_dep(dep):
    if dep == "node":
        try: subprocess.run(["node","--version"],capture_output=True,timeout=5); return True
        except: return False
    mod = {"PIL":"PIL","browser_use":"browser_use","composio_core":"composio"}.get(dep,dep)
    return importlib.util.find_spec(mod) is not None

def chk_opencode_json():
    issues, fixes = [], []
    if not OC.exists():
        return {"ok":False,"issues":["opencode.json not found"],"fixes":[f"Run install.ps1 to create it"]}
    try:
        raw = OC.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"ok":False,"issues":[f"JSON parse error: {e}"],"fixes":["python mcp_doctor.py --fix"]}
    
    mcp_issues = {}
    for name, cfg in data.get("mcp",{}).items():
        p = []
        if "type" in cfg:
            p.append("'type' field must be removed")
        if isinstance(cfg.get("command"), list):
            p.append("'command' must be string not list — use 'args' for extra args")
        if "environment" in cfg:
            p.append("'environment' must be renamed to 'env'")
        if p:
            mcp_issues[name] = p
            fixes.append(f"python mcp_doctor.py --fix")
    
    return {"ok":len(mcp_issues)==0,"issues":issues,"mcp_issues":mcp_issues,"fixes":fixes}

def chk_mcp(name, info):
    r = {"name":name,"status":"ok","issues":[],"fixes":[]}
    fname = info["file"]
    
    if fname is None:  # firecrawl / npx
        if not chk_dep("node"):
            r["status"]="warning"
            r["issues"].append("Node.js not installed (needed for firecrawl)")
            r["fixes"].append(DEP_FIX["node"])
        return r
    
    fpath = CFG / fname
    if not fpath.exists():
        r["status"]="error"
        r["issues"].append(f"File missing: {fpath}")
        r["fixes"].append(f"Re-run install.ps1 — it will copy {fname}")
        return r
    
    # Syntax check
    try:
        res = subprocess.run(["python","-m","py_compile",str(fpath)],
                             capture_output=True,text=True,timeout=10)
        if res.returncode != 0:
            r["status"]="error"
            r["issues"].append(f"Syntax error: {res.stderr.strip()[:200]}")
            r["fixes"].append(f"Fix syntax in {fname} — check stderr above")
            return r
    except Exception as e:
        r["status"]="warning"; r["issues"].append(f"Syntax check failed: {e}")
    
    # llm_fallback check
    if not (CFG/"llm_fallback.py").exists():
        r["status"]="error"
        r["issues"].append("llm_fallback.py missing — all MCPs need it")
        r["fixes"].append("Re-run install.ps1")
    
    # _mcp_base check
    if not (CFG/"_mcp_base.py").exists():
        r["status"]="error"
        r["issues"].append("_mcp_base.py missing — core base file")
        r["fixes"].append("Re-run install.ps1")
    
    # Dep check
    for dep in info["deps"]:
        if not chk_dep(dep):
            sev = "warning"
            r["status"] = sev
            r["issues"].append(f"Missing package: {dep}")
            r["fixes"].append(DEP_FIX.get(dep, f"pip install {dep}"))

    # browser_use version compatibility warning
    if name == "browser-use" and chk_dep("browser_use"):
        try:
            import importlib.metadata
            bu_ver = importlib.metadata.version("browser-use")
            major = int(bu_ver.split(".")[0])
            if major >= 1:
                r["issues"].append(f"browser-use v{bu_ver} detected — API changed in v1.x, result extraction uses multi-version fallback")
                r["fixes"].append("If browse tool returns garbled output: pip install 'browser-use<1.0'")
        except Exception:
            pass

    return r

def chk_mcp_live(name, info):
    """Actually ping the MCP server with initialize message."""
    fname = info.get("file")
    if not fname or info.get("async"): 
        return None  # skip async servers (they use mcp SDK differently)
    fpath = CFG / fname
    if not fpath.exists(): return "file_missing"
    try:
        proc = subprocess.run(
            ["python", str(fpath)],
            input=INIT_MSG+"\n", capture_output=True, text=True, timeout=8
        )
        out = proc.stdout.strip()
        if "protocolVersion" in out:
            return "ok"
        elif out:
            return f"bad_response: {out[:100]}"
        else:
            err = proc.stderr.strip()[-150:] if proc.stderr else "no output"
            return f"no_response: {err}"
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        return f"error: {e}"

# ── Auto-fix ─────────────────────────────────────────────────────────
def auto_fix():
    if not OC.exists():
        print("❌ opencode.json not found"); return
    try:
        data = json.loads(OC.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Cannot parse opencode.json: {e}"); return
    
    fixed = 0
    for name, cfg in data.get("mcp",{}).items():
        changed = False
        if "type" in cfg:
            del cfg["type"]; changed=True
        if isinstance(cfg.get("command"), list):
            parts = cfg["command"]
            cfg["command"] = parts[0]
            cfg["args"] = parts[1:] + list(cfg.get("args",[]))
            changed=True
        if "environment" in cfg:
            cfg["env"] = cfg.pop("environment"); changed=True
        if changed:
            fixed += 1; print(f"  🔧 Fixed: {name}")
    
    if fixed:
        bak = OC.with_suffix(".json.bak")
        bak.write_text(OC.read_text(encoding="utf-8"), encoding="utf-8")
        OC.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n✅ {fixed} entries fixed. Backup → {bak.name}")
        print("🔄 Restart OpenCode to apply.")
    else:
        print("✅ opencode.json looks clean — nothing to fix")

# ── Report ────────────────────────────────────────────────────────────
def run_check(live=False):
    report = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config_dir": str(CFG),
        "python": chk_python(),
        "opencode_json": chk_opencode_json(),
        "mcps": {},
        "summary": {"ok":0,"warning":0,"error":0}
    }
    for name, info in MCPS.items():
        r = chk_mcp(name, info)
        if live:
            r["live"] = chk_mcp_live(name, info)
        report["mcps"][name] = r
        report["summary"][r["status"]] = report["summary"].get(r["status"],0)+1
    return report

def print_report(rep, live=False):
    IC = {"ok":"✅","warning":"⚠️ ","error":"❌"}
    W  = 56
    print(f"\n{'═'*W}")
    print(f"  OpenWork MCP Doctor v8  —  {rep['ts']}")
    print(f"  {rep['config_dir']}")
    print(f"{'═'*W}")

    py = rep["python"]
    print(f"\n🐍 Python : {IC['ok'] if py['ok'] else IC['error']} {py['version']}" +
          (f"  ← {py['note']}" if py.get("note") else ""))

    oj = rep["opencode_json"]
    print(f"📋 Config  : {IC['ok'] if oj['ok'] else IC['error']} opencode.json", end="")
    if not oj["ok"]:
        for i in oj.get("issues",[]): print(f"\n   → {i}", end="")
        for n,ps in oj.get("mcp_issues",{}).items():
            for p in ps: print(f"\n   → [{n}] {p}", end="")
        if oj.get("fixes"): print(f"\n   💡 {oj['fixes'][0]}", end="")
    print()

    print(f"\n{'─'*W}  MCP Servers")
    ok_names, issue_names = [], []
    for name, r in rep["mcps"].items():
        if r["status"]=="ok": ok_names.append(name)
        else: issue_names.append((name,r))

    if ok_names:
        live_ok = [n for n in ok_names if rep["mcps"][n].get("live")=="ok"]
        live_unk= [n for n in ok_names if rep["mcps"][n].get("live") is None]
        others  = [n for n in ok_names if n not in live_ok and n not in live_unk]
        
        if live_ok:  print(f"\n✅  Online  : {', '.join(live_ok)}")
        if live_unk: print(f"✅  Ready   : {', '.join(live_unk)}")
        if others:   print(f"⚠️   Check   : {', '.join(others)}")

    for name, r in issue_names:
        crit = " [CRITICAL]" if MCPS[name].get("critical") else ""
        print(f"\n{IC[r['status']]} {name}{crit}")
        for issue in r["issues"]:
            print(f"   ⚠  {issue}")
        if r["fixes"]:
            print(f"   {'─'*40}")
            for fix in r["fixes"]:
                print(f"   💡 {fix}")
        if live and r.get("live"):
            print(f"   🔌 live ping: {r['live']}")

    s = rep["summary"]
    total = sum(s.values())
    print(f"\n{'═'*W}")
    print(f"  ✅ {s['ok']}/{total} OK  |  ⚠️  {s.get('warning',0)} warnings  |  ❌ {s.get('error',0)} errors")
    if s.get("error",0)==0 and s.get("warning",0)==0:
        print(f"  🚀 All systems go — OpenWork ready!")
    elif s.get("error",0)==0:
        print(f"  ⚡ Core MCPs healthy. Optional deps missing (see above).")
    else:
        print(f"  🔧 Fix errors above, then restart OpenCode.")
    print(f"{'═'*W}\n")

if __name__=="__main__":
    if "--fix" in sys.argv:
        print("🔧 Auto-fixing opencode.json...")
        auto_fix()
    elif "--json" in sys.argv:
        print(json.dumps(run_check(live="--test" in sys.argv), indent=2))
    elif "--watch" in sys.argv:
        live = "--test" in sys.argv
        print("👁  Watch mode — Ctrl+C to stop\n")
        while True:
            try:
                os.system("cls" if os.name=="nt" else "clear")
                print_report(run_check(live=live), live=live)
                time.sleep(15)
            except KeyboardInterrupt:
                print("\nStopped."); break
    elif "--test" in sys.argv:
        print("🔌 Live ping mode (tests actual server startup)...\n")
        print_report(run_check(live=True), live=True)
    else:
        print_report(run_check())
