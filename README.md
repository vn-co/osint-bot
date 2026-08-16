# osint-bot

Telegram Reconnaissance Bot — sends a target (username / email / domain) via `/recon` and runs the full OSINT toolchain.

## Structure

```
osint-bot/
├── bot.py          # Telegram entrypoint (/recon, /list, /start)
├── recon.py        # Orchestrator — shells out to tools, parses output, saves reports
├── config.py       # Paths, tool configs, env loading
├── tools/          # Source code for each OSINT tool
│   ├── sherlock/         Social media username search
│   ├── phoneinfoga/      Phone number intelligence
│   ├── theHarvester/     Domain/subdomain recon (email, hosts)
│   ├── sublist3r/       Subdomain enumeration
│   ├── social-analyzer/  Social profiling + confidence scoring
│   ├── spiderfoot/      OSINT framework with web UI
│   └── amass/           OWASP attack surface mapper
├── reports/          # Generated per-query (JSON or text)
├── .env              # TELEGRAM_BOT_TOKEN
└── requirements.txt
```

## Quick Start

```bash
cd osint-bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # paste your bot token from @BotFather
python3 bot.py
```

## Bot Commands

| Command | Action |
|---|---|
| `/start` | Usage info |
| `/list` | Available tools + their input types |
| `/recon <target>` | Run all tools |
| `/recon sherlock john_doe` | Single tool against target |

## Tool Coverage

| Purpose | Tool(s) | Status |
|---|---|---|
| Username correlation | sherlock, social-analyzer | pip + local |
| Email exposure check | holehe | pip |
| Phone recon | phoneinfoga | Go binary (install manually) |
| Domain/subdomain | theHarvester, sublist3r, amass | pip + local |
| Metadata extraction | spiderfoot (future exiftool) | web UI framework |
