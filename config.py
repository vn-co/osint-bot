"""Configuration for the OSINT bot."""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Local tool binary/script paths (fallbacks when not installed globally)
LOCAL_TOOLS: dict[str, list[str]] = {
    "sherlock":          lambda u: [str(TOOLS_DIR / "sherlock" / "sherlock_project"), "--username", u],
    "holehe":            lambda e: ["holehe", e],
    "phoneinfoga":       lambda p: [str(TOOLS_DIR / "phoneinfoga" / "phoneinfoga"), "scan", "-n", p],
    "theHarvester":      lambda d: ["python3", str(TOOLS_DIR / "theHarvester" / "theHarvester.py"), "-d", d, "-l", "100"],
    "sublist3r":         lambda d: ["python3", str(TOOLS_DIR / "sublist3r" / "sublist3r.py"), "-d", d],
    "social-analyzer":   lambda u: [str(TOOLS_DIR / "social-analyzer" / "app.py"), "--username", u],
    "spiderfoot":        lambda _: ["python3", str(TOOLS_DIR / "spiderfoot" / "sf.py"), "-m"],
}

# Input type expected per tool — used for validation at the bot layer
INPUT_MAP: dict[str, str] = {
    "sherlock":          "username",
    "holehe":            "email",
    "phoneinfoga":       "phone",
    "theHarvester":      "domain",
    "sublist3r":         "domain",
    "social-analyzer":   "username",
    "spiderfoot":        "module_args",
}

REPORT_FORMAT = "json"

# Ordered list of tool names — used as default for /recon
AVAILABLE_TOOLS: list[str] = list(LOCAL_TOOLS.keys())
