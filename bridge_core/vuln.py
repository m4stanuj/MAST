"""
M4STCLAW Vuln Scanner v2.0
============================
Ported from CAI upgrades vuln_mcp.py → FastAPI bridge style.

Tools:
  vuln_nmap     — Structured Nmap scan + AI parse
  vuln_nuclei   — Nuclei template-based vuln scan
  vuln_nikto    — Web server misconfiguration scan
  vuln_cve      — CVE details from NVD API
  vuln_analyze  — LLM analysis → prioritized report

Prerequisites:
  pip install requests
  nmap:    winget install nmap
  nuclei:  github.com/projectdiscovery/nuclei/releases → add to PATH
  nikto:   github.com/sullo/nikto (needs Perl)

AUTHORIZED USE ONLY — Always have written permission.
"""

import os, json, subprocess, re, time, socket, sys
from typing import Dict, Any, List, Optional
from pathlib import Path

ROOT = Path(__file__).parent.parent

def _brain(prompt: str, max_tokens: int = 700) -> str:
    try:
        sys.path.insert(0, str(ROOT / "bridge_core"))
        from brain import brain_quick
        return brain_quick(prompt, task_type="pentest", max_tokens=max_tokens)
    except Exception as e:
        return f"[brain unavailable: {e}]"

def _run(cmd: list, timeout: int = 120) -> tuple:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
        return r.returncode == 0, (r.stdout + "\n" + r.stderr).strip()
    except FileNotFoundError:
        return False, f"NOT_FOUND:{cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s"
    except Exception as e:
        return False, f"ERROR: {e}"


# ══════════════════════════════════════════════════════════════════════
#  NMAP
# ══════════════════════════════════════════════════════════════════════

def vuln_nmap(target: str, mode: str = "quick") -> Dict[str, Any]:
    """
    Nmap scan with service/version detection.
    mode: quick | vuln | full | udp
    """
    mode_args = {
        "quick":  ["-sV", "-T4", "--top-ports", "1000", "--open"],
        "vuln":   ["-sV", "-T4", "--script=vuln", "--top-ports", "200"],
        "full":   ["-sV", "-T4", "-p-", "--open"],
        "udp":    ["-sU", "-T3", "--top-ports", "100"],
        "smb":    ["-p", "139,445", "--script=smb-vuln*", "-T4"],
        "http":   ["-p", "80,443,8080,8443", "--script=http-vuln*,http-enum", "-T4"],
    }
    args = mode_args.get(mode, mode_args["quick"])
    ok, raw = _run(["nmap"] + args + ["-oX", "-", target], timeout=180)

    if not ok and "NOT_FOUND" in raw:
        return {"error": "nmap not found. Install: winget install nmap", "target": target}

    # Parse structured output
    ports = []
    for line in raw.splitlines():
        m = re.match(r"\s*(\d+)/(\w+)\s+(open|filtered)\s+(\S+)\s*(.*)", line)
        if m:
            ports.append({
                "port": int(m.group(1)),
                "proto": m.group(2),
                "state": m.group(3),
                "service": m.group(4),
                "version": m.group(5).strip(),
            })

    # Extract script output (vuln findings)
    vuln_findings = []
    current_vuln = None
    for line in raw.splitlines():
        if "VULNERABLE" in line or "CVE-" in line:
            vuln_findings.append(line.strip())
        if "|_" in line and current_vuln:
            vuln_findings.append(line.strip())

    result = {
        "target": target, "mode": mode,
        "ports": ports, "vuln_findings": vuln_findings[:20],
        "raw_snippet": raw[:3000],
    }

    if ports or vuln_findings:
        result["analysis"] = _brain(
            f"Nmap scan analysis for {target} (mode={mode}).\n"
            f"Open ports: {ports[:10]}\nVuln findings: {vuln_findings[:5]}\n"
            f"Prioritize: critical vulns, exploitable services, recommended next steps.",
        )

    return result


# ══════════════════════════════════════════════════════════════════════
#  NUCLEI
# ══════════════════════════════════════════════════════════════════════

def vuln_nuclei(target: str, severity: str = "medium,high,critical",
                templates: str = "cves,exposures,misconfigurations") -> Dict[str, Any]:
    """Nuclei template-based vulnerability scan."""
    cmd = ["nuclei", "-u", target, "-severity", severity,
           "-t", templates, "-j", "-timeout", "10", "-silent"]
    ok, out = _run(cmd, timeout=120)

    if not ok and "NOT_FOUND" in out:
        return {
            "error": "nuclei not found. Download: github.com/projectdiscovery/nuclei/releases",
            "target": target,
            "note": "Add nuclei.exe to PATH after download",
        }

    findings = []
    for line in out.splitlines():
        line = line.strip()
        if not line: continue
        try:
            finding = json.loads(line)
            findings.append({
                "template_id": finding.get("template-id", ""),
                "name": finding.get("info", {}).get("name", ""),
                "severity": finding.get("info", {}).get("severity", ""),
                "matched_at": finding.get("matched-at", ""),
                "description": finding.get("info", {}).get("description", "")[:200],
                "tags": finding.get("info", {}).get("tags", []),
            })
        except json.JSONDecodeError:
            if "[" in line:  # Non-JSON output
                findings.append({"raw": line})

    result = {
        "target": target, "severity_filter": severity,
        "findings_count": len(findings), "findings": findings,
    }

    if findings:
        result["analysis"] = _brain(
            f"Nuclei scan results for {target}: {len(findings)} findings.\n"
            f"Top findings: {json.dumps(findings[:5], default=str)[:1500]}\n"
            f"Risk assessment and recommended immediate actions.",
        )

    return result


# ══════════════════════════════════════════════════════════════════════
#  NIKTO (web server)
# ══════════════════════════════════════════════════════════════════════

def vuln_nikto(target: str, port: int = 80) -> Dict[str, Any]:
    """Nikto web server scan — finds misconfigs, outdated software, dangerous files."""
    url = target if target.startswith("http") else f"http://{target}:{port}"
    ok, out = _run(["nikto", "-h", url, "-Format", "txt", "-timeout", "10"], timeout=120)

    if not ok and "NOT_FOUND" in out:
        return {
            "error": "nikto not found. Requires Perl. Download: github.com/sullo/nikto",
            "target": target,
        }

    # Parse findings
    findings = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("+") and "OSVDB" not in line:
            findings.append(line.lstrip("+ "))

    return {
        "target": target, "port": port,
        "findings": findings[:30],
        "raw": out[:2000],
        "analysis": _brain(
            f"Nikto web scan for {target}:{port}.\n"
            f"Findings: {findings[:10]}\nRisk level + critical issues.",
        ) if findings else "No significant findings.",
    }


# ══════════════════════════════════════════════════════════════════════
#  CVE LOOKUP
# ══════════════════════════════════════════════════════════════════════

def vuln_cve(cve_id: str) -> Dict[str, Any]:
    """CVE details from NVD API (free, no key needed)."""
    import requests
    try:
        # NVD API v2
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id.upper()}"
        r = requests.get(url, timeout=10, headers={"User-Agent": "M4STCLAW-v2"})
        r.raise_for_status()
        data = r.json()

        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return {"error": f"{cve_id} not found in NVD", "cve_id": cve_id}

        cve_data = vulns[0]["cve"]
        desc_list = cve_data.get("descriptions", [])
        description = next((d["value"] for d in desc_list if d["lang"] == "en"), "No description")

        # CVSS score
        score = None
        severity = None
        metrics = cve_data.get("metrics", {})
        for key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
            if key in metrics and metrics[key]:
                cvss = metrics[key][0].get("cvssData", {})
                score = cvss.get("baseScore")
                severity = cvss.get("baseSeverity")
                break

        # References
        refs = [r["url"] for r in cve_data.get("references", [])[:5]]

        return {
            "cve_id": cve_id.upper(),
            "description": description[:500],
            "cvss_score": score,
            "severity": severity,
            "published": cve_data.get("published", ""),
            "last_modified": cve_data.get("lastModified", ""),
            "references": refs,
            "cpe": [c.get("criteria") for c in cve_data.get("configurations", [{}])[0]
                    .get("nodes", [{}])[0].get("cpeMatch", [])[:5]] if cve_data.get("configurations") else [],
        }

    except requests.RequestException as e:
        return {"error": f"NVD API error: {e}", "cve_id": cve_id}


# ══════════════════════════════════════════════════════════════════════
#  VULNERABILITY ANALYSIS
# ══════════════════════════════════════════════════════════════════════

def vuln_analyze(target: str, findings: List[Dict]) -> Dict[str, Any]:
    """AI analysis of vulnerability findings → prioritized report."""
    report = _brain(
        f"Senior penetration tester. Create vulnerability report for {target}.\n"
        f"Findings: {json.dumps(findings, default=str)[:3000]}\n\n"
        f"Format:\n"
        f"## Executive Summary\n"
        f"## Critical Findings (act now)\n"
        f"## High Findings\n"
        f"## Medium Findings\n"
        f"## Recommended Remediation Steps\n"
        f"## Next Test Suggestions\n"
        f"Be technical but clear. Hinglish OK.",
        max_tokens=1200,
    )
    return {
        "target": target,
        "findings_count": len(findings),
        "report": report,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
