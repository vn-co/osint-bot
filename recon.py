"""Reconnaissance orchestrator — runs OSINT tools and merges results."""

import json
import subprocess
import traceback
from pathlib import Path
from datetime import datetime, timezone

from config import LOCAL_TOOLS, INPUT_MAP, REPORTS_DIR


def _run(tool: str, target: str) -> dict:
    """Run a single tool against *target*. Returns {success, output, error}."""
    try:
        cmd = LOCAL_TOOLS[tool](target)
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
        )
        return {
            "tool": tool,
            "target": target,
            "success": result.returncode == 0 or bool(result.stdout.strip()),
            "output": result.stdout[:10_000] if result.stdout else "",
            "error": result.stderr[:3_000] if result.stderr and result.returncode != 0 else "",
        }
    except FileNotFoundError:
        return {"tool": tool, "target": target, "success": False, "output": "", "error": f"'{cmd[0]}' not found — install the tool first"}
    except subprocess.TimeoutExpired:
        return {"tool": tool, "target": target, "success": False, "output": "", "error": "timed out (180s)"}
    except Exception as e:
        return {"tool": tool, "target": target, "success": False, "output": "", "error": str(e)}


# ---------------------------------------------------------------------------
# Per-tool parsers — turn raw output into structured dicts
# ---------------------------------------------------------------------------

def _parse_sherlock(raw: str) -> list[dict]:
    """Parse sherlock's JSON output."""
    results = []
    for line in raw.strip().splitlines():
        try:
            data = json.loads(line)
            site = data.get("site_name", "unknown")
            url = data.get("url_reported", "") or data.get("url", "")
            status = data.get("status", {}).get("status_text", "unknown") if isinstance(data.get("status"), dict) else "unknown"
            results.append({"site": site, "url": url, "status": status})
        except (json.JSONDecodeError, TypeError):
            pass
    return results


def _parse_theharvester(raw: str) -> list[dict]:
    """Parse theHarvester's tabular output."""
    entries = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) >= 2:
            entries.append({"ip": parts[0], "hostname": parts[-1]})
    return entries


def _parse_sublist3r(raw: str) -> list[str]:
    """Parse sublist3r domain list output."""
    domains = []
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("[") and ":" not in line:
            domains.append(line)
    return domains


def _parse_social_analyzer(raw: str) -> list[dict]:
    """Parse social-analyzer results (may be mixed JSON/text)."""
    sites = []
    for line in raw.splitlines():
        try:
            data = json.loads(line)
            sites.append(data.get("data", data))
        except json.JSONDecodeError:
            pass
    return sites


# Parsers keyed by tool name. Each takes raw stdout → structured list.
PARSERS = {
    "sherlock": _parse_sherlock,
    "theHarvester": _parse_theharvester,
    "sublist3r": _parse_sublist3r,
    "social-analyzer": _parse_social_analyzer,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_recon(target: str, tools: list[str] | None = None) -> dict:
    """Run *tools* against *target*. Returns a merged report dict."""
    if tools is None:
        tools = list(LOCAL_TOOLS.keys())

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "input_type": INPUT_MAP.get(tools[0], "unknown") if tools else "",
        "results": {},
    }

    for tool in tools:
        tool_output = _run(tool, target)
        report["results"][tool] = {
            "success": tool_output["success"],
            "entries": PARSERS[tool](tool_output["output"]) if tool in PARSERS else [],
            "raw": tool_output["output"][:5_000] if tool_output["output"] else "",
        }
        if not tool_output["error"]:
            report["results"][tool]["error"] = tool_output["error"]

    return report


def save_report(report: dict, fmt: str = "json") -> Path:
    """Write report to reports/ and return the file path."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_target = "".join(c if c.isalnum() else "_" for c in report["target"][:30])

    if fmt == "json":
        filepath = REPORTS_DIR / f"report-{safe_target}-{ts}.json"
        filepath.write_text(json.dumps(report, indent=2, default=str))
    else:
        filepath = REPORTS_DIR / f"report-{safe_target}-{ts}.txt"
        lines = [f"# OSINT Report — {report['target']}"]
        lines.append(f"# Generated: {report['generated_at']}")
        lines.append("")
        for tool, data in report["results"].items():
            lines.append(f"## {tool}")
            lines.append(f"Status: {'OK' if data['success'] else 'FAIL'}")
            entries = data.get("entries", [])
            if isinstance(entries, list):
                for e in (entries[:50] if len(entries) > 50 else entries):
                    if isinstance(e, dict):
                        lines.append(json.dumps(e))
                    else:
                        lines.append(str(e))
            raw = data.get("raw", "")
            if raw and not entries:
                lines.append(raw)
            lines.append("")
        filepath.write_text("\n".join(lines))

    return filepath


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "testuser"
    tool_list = sys.argv[2].split(",") if len(sys.argv) > 2 else ["sherlock"]
    print(f"[recon] Running {tool_list} against '{target}' ...")
    report = run_recon(target, tool_list)
    path = save_report(report)
    print(f"[recon] Report saved to {path}")
    # Print summary
    for tool, data in report["results"].items():
        count = len(data.get("entries", []))
        status = "OK" if data["success"] else f"FAIL ({data.get('error', '')[:40]})"
        print(f"  {tool:20s} → {status} ({count} entries)")
