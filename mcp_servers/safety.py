"""
M4STCLAW Safety Guard v2.0
============================
Destructive command protection. Ported from OpenWork v12 safety-net skill.
Blocks rm -rf, git reset --hard, force push etc before execution.
Used by tools.py before any shell command.
"""

import re
from typing import Tuple

# ── Danger patterns ───────────────────────────────────────────────────
_DANGER_PATTERNS = [
    # Filesystem
    (r"rm\s+-[rRf]{2,}\s+[/~*]",       "rm -rf on root/home/glob — DATA LOSS"),
    (r"rm\s+-[rRf]+\s+\*",              "rm -rf * — akan delete everything here"),
    (r"del\s+/[fFsS]",                  "Windows del /f /s — mass delete"),
    (r"rmdir\s+/[sS]",                  "rmdir /s — recursive directory delete"),
    (r"format\s+[a-zA-Z]:",             "format drive — DISK WIPE"),
    (r"rd\s+/[sS]",                     "rd /s — recursive delete"),
    # Git danger
    (r"git\s+reset\s+--hard",           "git reset --hard — undo uncommitted work"),
    (r"git\s+push\s+--force(?!\s*-with-lease)", "git push --force — overwrites remote history"),
    (r"git\s+clean\s+-[fF][dD]?",       "git clean -fd — deletes untracked files"),
    (r"git\s+branch\s+-[Dd]\s+main",    "delete main branch"),
    (r"git\s+branch\s+-[Dd]\s+master",  "delete master branch"),
    # Python danger
    (r"shutil\.rmtree\(['\"]?[/C]",     "shutil.rmtree on root/C: path"),
    (r"os\.remove.*\.env",              "deleting .env file — API keys gone"),
    # Database
    (r"DROP\s+TABLE",                   "SQL DROP TABLE — permanent data loss"),
    (r"DROP\s+DATABASE",                "SQL DROP DATABASE"),
    (r"TRUNCATE\s+TABLE",               "SQL TRUNCATE — clears all rows"),
    # Network danger
    (r"wget.*\|\s*sh",              "wget pipe to shell — remote code execution"),
    (r"curl.*\|\s*sh",              "curl pipe to shell — remote code execution"),
    (r"wget.*\|\s*bash",            "wget pipe to bash — remote code execution"),
    (r"curl.*\|\s*bash",            "curl pipe to bash — remote code execution"),
    (r"iptables\s+-F",                  "iptables flush — kills all firewall rules"),
    (r"netsh\s+advfirewall\s+reset",    "Windows firewall reset"),
    # M4STCLAW specific
    (r"del.*memory\.json",              "deleting memory file — all MAST memory lost"),
    (r"del.*pentest_memory\.json",      "deleting pentest memory — all target data lost"),
    (r"del.*\.env",                     "deleting .env — all API keys gone"),
    (r"rm.*opencode\.json",             "deleting OpenClaw config"),
]

# ── Warning patterns (warn but don't block) ────────────────────────────
_WARN_PATTERNS = [
    (r"rmdir\s+[^\s]+",                 "rmdir without /s — single dir delete"),
    (r"git\s+stash\s+drop",             "git stash drop — loses stashed work"),
    (r"git\s+branch\s+-[Dd]",          "git branch delete"),
    (r"pip\s+uninstall",                "uninstalling package"),
    (r"del\s+[^\s]+",                   "Windows file delete"),
    (r"rm\s+[^\s]+",                    "file delete"),
]

# ── M4STCLAW specific safe dirs (never touch) ─────────────────────────
_PROTECTED_PATHS = [
    r"[\\/]\.config[\\/]opencode[\\/]",
    r"[\\/]\.env$",
    r"memory\.json",
    r"pentest_memory\.json",
    r"opencode\.json",
    r"openclaw\.config\.json",
    r"SOUL\.md",
]


def check_command(cmd: str) -> Tuple[bool, str, str]:
    """
    Check a shell command for danger.
    Returns: (is_safe, level, message)
      level: "ok" | "warn" | "block"
    """
    cmd_lower = cmd.lower().strip()

    # Check protected paths first
    for path_pat in _PROTECTED_PATHS:
        if re.search(path_pat, cmd, re.IGNORECASE):
            if any(op in cmd_lower for op in ["rm ", "del ", "delete", "rmdir", "erase"]):
                return False, "block", f"⛔ BLOCKED — Touching protected MAST config file: {path_pat}"

    # Check danger patterns
    for pattern, reason in _DANGER_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return False, "block", f"⛔ BLOCKED — {reason}\nCommand: {cmd}\nType 'confirm: {cmd}' to override."

    # Check warning patterns
    for pattern, reason in _WARN_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, "warn", f"⚠️ WARNING — {reason}\nCommand: {cmd}\nProceed with caution."

    return True, "ok", ""


def safe_exec(cmd: str, confirm_prefix: str = "confirm:") -> Tuple[bool, str]:
    """
    Wrap around shell execution. Returns (can_execute, message).
    If user prefixes command with "confirm:", bypasses safety checks.
    """
    # Explicit confirmation override
    if cmd.strip().lower().startswith(confirm_prefix):
        actual_cmd = cmd[len(confirm_prefix):].strip()
        return True, actual_cmd

    is_safe, level, msg = check_command(cmd)

    if level == "block":
        return False, msg
    elif level == "warn":
        return True, msg  # Execute but warn
    else:
        return True, cmd


def check_file_operation(path: str, operation: str) -> Tuple[bool, str]:
    """Check file operations (delete, overwrite) for safety."""
    for pat in _PROTECTED_PATHS:
        if re.search(pat, path, re.IGNORECASE):
            return False, f"⛔ {operation} blocked — protected path: {path}"
    return True, ""


def get_safe_alternatives(blocked_cmd: str) -> str:
    """Suggest safer alternatives for blocked commands."""
    cmd_l = blocked_cmd.lower()
    suggestions = []

    if "git reset --hard" in cmd_l:
        suggestions = [
            "git stash                  # save changes instead",
            "git reset --soft HEAD~1    # undo commit, keep changes",
            "git restore .              # discard working tree changes only",
        ]
    elif "git push --force" in cmd_l and "--force-with-lease" not in cmd_l:
        suggestions = ["git push --force-with-lease  # safer force push"]
    elif "rm -rf" in cmd_l:
        suggestions = [
            "mv <dir> /tmp/backup_$(date +%s)  # move to temp instead of delete",
            "rm -rf <specific_path>             # use explicit path, not wildcards",
        ]
    elif "drop table" in cmd_l:
        suggestions = [
            "ALTER TABLE ... RENAME TO backup_...  # rename instead of drop",
            "CREATE TABLE backup AS SELECT * FROM ...  # backup first",
        ]

    if suggestions:
        return "💡 Safe alternatives:\n" + "\n".join(f"  {s}" for s in suggestions)
    return ""
