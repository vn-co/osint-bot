"""Telegram OSINT bot — /recon <username/email/domain>."""

import asyncio
import logging
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, REPORT_FORMAT, LOCAL_TOOLS, INPUT_MAP, AVAILABLE_TOOLS
from recon import run_recon, save_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "OSINT Recon Bot\n"
        "\n"
        "Usage:\n"
        "  /recon <target>              — run all tools\n"
        "  /recon sherlock <username>   — single tool\n"
        "  /list                        — available tools\n"
        "\n"
        "Targets: usernames, emails, domains, phone numbers (per tool)."
    )


AVAILABLE_TOOLS = list(LOCAL_TOOLS.keys())

async def list_tools(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = ["Available tools:\n"]
    for name, input_type in INPUT_MAP.items():
        has_local = name in LOCAL_TOOLS
        lines.append(f"  • {name:<20s} [{input_type}] {'✓ local' if has_local else '○'}")
    await update.message.reply_text("\n".join(lines))


async def recon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = (context.args or []) if context.args else []

    if len(args) < 1:
        await update.message.reply_text("Usage: /recon sherlock john_doe")
        return

    if len(args) == 1:
        # All tools, single target
        target = args[0]
        tools_run = AVAILABLE_TOOLS
    else:
        # tool_name target [extra_args...]
        tools_run = [args[0]]
        target = args[1]

    # Send a "running" message so the user knows something is happening
    status_msg = await update.message.reply_text(
        f"🔍 Running {'all ' if len(args) == 1 else ''}recon on *{target}*\n⏳ Stand by..."
    )

    try:
        report = run_recon(target, tools_run)
        path = save_report(report, REPORT_FORMAT)

        # Send summary as text (long reports as a file)
        summary_lines = [f"🔍 Report for `{target}` ({report['generated_at'][:16]} UTC):"]
        found_any = False
        for tool, data in report["results"].items():
            count = len(data.get("entries", []))
            status_icon = "OK" if data["success"] else "FAIL"
            summary_lines.append(f"  • {tool:<20s} → {status_icon} ({count} entries)")
            if count > 0:
                found_any = True

        # If there are results, send the report file
        report_text = path.read_text()
        if len(report_text) < 4_000:
            # Inline is fine
            await update.message.reply_text(f"\n".join(summary_lines) + "\n\n📄 Full results:", parse_mode="Markdown")
            await update.message.reply_text(report_text[:4096] if len(report_text) > 4096 else report_text)
        else:
            # Send as file
            with open(path, "rb") as f:
                await update.message.reply_document(f, filename=path.name)

        await status_msg.edit_text(
            "\n".join(summary_lines) + ("\n\n✅ Done." if found_any else "\n\n⚠️ Nothing found.")
        )

    except Exception as e:
        log.exception("Recon failed for %s", target)
        await status_msg.edit_text(f"❌ Error running recon on `{target}`:\n```\n{e}\n```", parse_mode="Markdown")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is empty — set it in .env")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("recon", recon))
    app.add_handler(CommandHandler("list", list_tools))
    log.info("Starting bot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
