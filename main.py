"""
main.py — Chạy đồng thời:
  1. Discord bot (discord.py)
  2. FastAPI webhook server (uvicorn) để nhận event từ SePay

Cả hai chạy trong cùng một event loop qua asyncio.
"""

import asyncio
import logging

import discord
from discord import app_commands
import uvicorn
from fastapi import FastAPI

import config
from handlers import webhook, commands, scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("expense_bot")


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="Expense Bot Webhook")
app.include_router(webhook.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Discord bot ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

commands.setup_commands(bot, tree)


@bot.event
async def on_ready():
    log.info(f"Discord bot logged in as {bot.user}")

    # Sync slash commands lên Discord
    try:
        synced = await tree.sync()
        log.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        log.error(f"Failed to sync commands: {e}")

    # Inject bot vào webhook handler
    webhook.set_discord_bot(bot)

    # Khởi động scheduler
    scheduler.start(bot)
    log.info("Scheduler started")


# ── Run both concurrently ──────────────────────────────────────────────────────
async def main():
    if not config.DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN chưa được set trong .env")
    if not config.SPREADSHEET_ID:
        raise RuntimeError("SPREADSHEET_ID chưa được set trong .env")

    uvicorn_config = uvicorn.Config(
        app,
        host=config.WEBHOOK_HOST,
        port=config.WEBHOOK_PORT,
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)

    # Chạy cả hai trong cùng event loop
    await asyncio.gather(
        bot.start(config.DISCORD_BOT_TOKEN),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())