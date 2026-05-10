"""
M4STCLAW Recon v2.0 — OSINT & Reconnaissance
==============================================
Ported from CAI upgrades recon_mcp.py → FastAPI bridge style.
Cybersecurity background ke liye — Mast ka CEH toolkit.

Tools:
  recon_shodan    — IP/domain: open ports, CVEs, org info
  recon_subfinder — Passive subdomain enumeration
  recon_whois     — Domain registration details
  recon_dns       — DNS records: A/MX/TXT/NS/CNAME
  recon_portscan  — Quick nmap wrapper (top 1000 ports)
  recon_harvester — Email/subdomain harvesting
  recon_summary   — Full OSINT run → save to pentest memory

Prerequisites:
  pip install requests python-whois dnspython shodan
  # Optional binaries (better results):
  # nmap, subfinder, theHarvester

AUTHORIZED USE ONLY — Always have written permission.
"""

import os, sys, json, time, subprocess, socket, re
from typing import Dict, Any, Optional
from pathlib import Path

ROOT = Path(__file__).parent.parent

def _cfg(key): 
    try:
        with open(ROOT / "config" / ".env", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("#") or "=" not in line: continue
                k, v = line.strip().split("=", 1)
                if k.strip() == key: return v.strip().strip('"').strip("'")
    except: pass
    return os.environ.get(key, "")

def _brain(prompt: str, max_tokens: int = 600) -> str:
    try:
        sys.path.insert(0, str(ROOT / "bridge_core"))
        from brain import brain_quick
        return brain_quick(prompt, task_type="pentest", max_tokens=max_tokens)
    except Exception as e:
        return f"[brain unavailable: {e}]"

def _run(cmd: list, timeout: int = 60) -> tuple:
    """Run shell command, return (ok, output)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
        return r.returncode == 0, (r.stdout + "\n" + r.stderr).strip()
    except FileNotFoundError:
        return False, f"NOT_FOUND:{cmd[0]} — install it first"
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s"
    except Exception as e:
        return False, f"ERROR: {e}"


# ══════════════════════════════════════════════════════════════════════
#  SHODAN
# ══════════════════════════════════════════════════════════════════════

def recon_shodan(target: str) -> Dict[str, Any]:
    """Shodan scan — ports, CVEs, org info for IP/domain."""
    api_key = _cfg("SHODAN_API_KEY")
    if not api_key:
        return {"error": "SHODAN_API_KEY not set. Free key: account.shodan.io"}

    try:
        import shodan
        api = shodan.Shodan(api_key)
        # Resolve domain to IP if needed
        try:
            ip = socket.gethostbyname(target)
        except:
            ip = target

        host = api.host(ip)
        result = {
            "ip": ip,
            "target": target,
            "org": host.get("org", "Unknown"),
            "country": host.get("country_name", "Unknown"),
            "city": host.get("city", "Unknown"),
            "os": host.get("os"),
            "ports": sorted(host.get("ports", [])),
            "hostnames": host.get("hostnames", []),
            "cves": [],
            "services": [],
            "raw_count": len(host.get("data", [])),
        }
        for item in host.get("data", [])[:10]:
            svc = {
                "port": item.get("port"),
                "transport": item.get("transport", "tcp"),
                "product": item.get("product", ""),
                "version": item.get("version", ""),
                "banner": item.get("banner", "")[:200],
            }
            result["services"].append(svc)
            # Extract CVEs from vulns
            for vuln_id in item.get("vulns", {}).keys():
                if vuln_id not in result["cves"]:
                    result["cves"].append(vuln_id)

        # AI analysis
        result["analysis"] = _brain(
            f"Cybersecurity analyst. Analyze Shodan data for {target}.\n"
            f"Ports: {result['ports']}\nServices: {result['services'][:3]}\nCVEs: {result['cves']}\n"
            f"Findings: key attack surface, risk level (Low/Med/High/Critical). Be concise.",
        )
        return result

    except ImportError:
        return {"error": "shodan not installed: pip install shodan"}
    except Exception as e:
        return {"error": f"Shodan error: {e}", "target": target}


# ══════════════════════════════════════════════════════════════════════
#  WHOIS
# ══════════════════════════════════════════════════════════════════════

def recon_whois(domain: str) -> Dict[str, Any]:
    """WHOIS registration details."""
    try:
        import whois
        w = whois.whois(domain)
        return {
            "domain": domain,
            "registrar": str(w.registrar or ""),
            "creation_date": str(w.creation_date or ""),
            "expiration_date": str(w.expiration_date or ""),
            "updated_date": str(w.updated_date or ""),
            "name_servers": [str(ns) for ns in (w.name_servers or [])],
            "status": [str(s) for s in (w.status or []) if s][:5],
            "emails": list(set([str(e) for e in (w.emails or []) if e])),
            "org": str(w.org or ""),
            "country": str(w.country or ""),
        }
    except ImportError:
        return {"error": "python-whois not installed: pip install python-whois"}
    except Exception as e:
        return {"error": f"WHOIS failed: {e}", "domain": domain}


# ══════════════════════════════════════════════════════════════════════
#  DNS
# ══════════════════════════════════════════════════════════════════════

def recon_dns(domain: str) -> Dict[str, Any]:
    """DNS records — A, MX, TXT, NS, CNAME + zone transfer attempt."""
    try:
        import dns.resolver
        result = {"domain": domain, "records": {}}
        record_types = ["A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA"]

        for rtype in record_types:
            try:
                answers = dns.resolver.resolve(domain, rtype)
                result["records"][rtype] = [str(r) for r in answers]
            except Exception:
                pass

        # Zone transfer attempt (usually fails — just for completeness)
        ns_list = result["records"].get("NS", [])
        result["zone_transfer"] = "not_attempted"
        if ns_list:
            ns = str(ns_list[0]).rstrip(".")
            try:
                import dns.zone, dns.query
                zone = dns.zone.from_xfr(dns.query.xfr(ns, domain, timeout=5))
                result["zone_transfer"] = f"SUCCESS — {len(list(zone.nodes.keys()))} records"
            except Exception:
                result["zone_transfer"] = "refused (expected)"

        return result

    except ImportError:
        return {"error": "dnspython not installed: pip install dnspython"}
    except Exception as e:
        return {"error": f"DNS failed: {e}", "domain": domain}


# ══════════════════════════════════════════════════════════════════════
#  SUBFINDER (subdomain enum)
# ══════════════════════════════════════════════════════════════════════

def recon_subfinder(domain: str, timeout: int = 30) -> Dict[str, Any]:
    """Passive subdomain enumeration using subfinder binary."""
    ok, out = _run(["subfinder", "-d", domain, "-silent", "-timeout", "10"], timeout=timeout)
    if not ok and "NOT_FOUND" in out:
        # Fallback: DNS brute-force top 20 common subdomains
        common = ["www","mail","ftp","admin","api","dev","test","app","blog","shop",
                  "portal","vpn","remote","cdn","static","assets","docs","support","m","mx"]
        found = []
        for sub in common:
            try:
                socket.gethostbyname(f"{sub}.{domain}")
                found.append(f"{sub}.{domain}")
            except: pass
        return {"domain": domain, "subdomains": found, "method": "dns_bruteforce_fallback",
                "note": "subfinder not found — install from github.com/projectdiscovery/subfinder"}
    subdomains = [s.strip() for s in out.splitlines() if s.strip() and domain in s]
    return {"domain": domain, "subdomains": subdomains, "count": len(subdomains), "method": "subfinder"}


# ══════════════════════════════════════════════════════════════════════
#  PORT SCAN (nmap wrapper)
# ══════════════════════════════════════════════════════════════════════

def recon_portscan(target: str, mode: str = "quick") -> Dict[str, Any]:
    """Quick nmap port scan. mode: quick|full|stealth"""
    modes = {
        "quick":   ["-T4", "--top-ports", "1000", "-sV"],
        "full":    ["-T4", "-p-", "-sV", "--open"],
        "stealth": ["-T2", "-sS", "--top-ports", "500"],
        "udp":     ["-sU", "--top-ports", "100", "-T3"],
    }
    nmap_args = modes.get(mode, modes["quick"])
    ok, out = _run(["nmap"] + nmap_args + ["-oN", "-", target], timeout=120)

    if not ok and "NOT_FOUND" in out:
        # Pure Python socket fallback
        open_ports = []
        top_ports = [21,22,23,25,53,80,110,135,139,143,443,445,993,995,1723,3306,3389,5432,5900,8080,8443]
        for port in top_ports:
            try:
                s = socket.socket()
                s.settimeout(0.5)
                if s.connect_ex((target, port)) == 0:
                    open_ports.append(port)
                s.close()
            except: pass
        return {"target": target, "open_ports": open_ports, "method": "socket_fallback",
                "note": "nmap not found — install: winget install nmap"}

    # Parse nmap output
    open_ports = []
    for line in out.splitlines():
        m = re.match(r"(\d+)/(\w+)\s+open\s+(.+)", line.strip())
        if m:
            open_ports.append({"port": int(m.group(1)), "proto": m.group(2), "service": m.group(3).strip()})

    return {
        "target": target, "mode": mode,
        "open_ports": open_ports,
        "count": len(open_ports),
        "raw": out[:2000],
        "analysis": _brain(f"Analyze port scan results for {target}:\n{out[:1500]}\nRisk level + attack surface.") if open_ports else "",
    }


# ══════════════════════════════════════════════════════════════════════
#  FULL OSINT SUMMARY
# ══════════════════════════════════════════════════════════════════════

def recon_summary(target: str) -> Dict[str, Any]:
    """Full OSINT — runs whois + dns + subfinder + portscan → AI summary."""
    print(f"[RECON] Starting full OSINT for {target}...", flush=True)
    results = {"target": target, "timestamp": time.time()}

    # Determine if IP or domain
    is_ip = bool(re.match(r"^\d+\.\d+\.\d+\.\d+$", target))

    if not is_ip:
        print(f"[RECON] WHOIS...", flush=True)
        results["whois"] = recon_whois(target)
        print(f"[RECON] DNS...", flush=True)
        results["dns"] = recon_dns(target)
        print(f"[RECON] Subdomains...", flush=True)
        results["subdomains"] = recon_subfinder(target, timeout=20)

    print(f"[RECON] Port scan...", flush=True)
    results["portscan"] = recon_portscan(target, mode="quick")

    # Shodan if key available
    if _cfg("SHODAN_API_KEY"):
        print(f"[RECON] Shodan...", flush=True)
        results["shodan"] = recon_shodan(target)

    # Final AI synthesis
    summary_data = {
        "ports": results.get("portscan", {}).get("open_ports", []),
        "subdomains": results.get("subdomains", {}).get("subdomains", [])[:10],
        "cves": results.get("shodan", {}).get("cves", []),
        "org": results.get("shodan", {}).get("org", results.get("whois", {}).get("org", "unknown")),
    }
    results["ai_summary"] = _brain(
        f"Cybersecurity OSINT report for {target}.\n"
        f"Data: {json.dumps(summary_data, default=str)[:2000]}\n"
        f"Write: Executive Summary, Attack Surface, Top 3 Risks, Recommended Tests. Hinglish OK.",
        max_tokens=800
    )

    # Save to pentest memory if available
    try:
        sys.path.insert(0, str(ROOT / "bridge_core"))
        from pentest_memory import pt_target_save
        pt_target_save(target, {
            "recon_done": True, "ports": summary_data["ports"],
            "subdomains": summary_data["subdomains"][:5],
            "cves": summary_data["cves"],
        })
        results["saved_to_memory"] = True
    except Exception:
        results["saved_to_memory"] = False

    return results
