"""
Webhook handler cho SePay.
Khi có giao dịch → gửi Discord message kèm buttons chọn category 2 tầng.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
import discord as discord_lib

import config
from services import sheets

router = APIRouter()

_discord_bot: discord_lib.Client | None = None
_pending_transactions: dict[str, dict] = {}


def set_discord_bot(bot: discord_lib.Client):
    global _discord_bot
    _discord_bot = bot


def get_pending(tx_id: str) -> dict | None:
    return _pending_transactions.get(tx_id)


def remove_pending(tx_id: str):
    _pending_transactions.pop(tx_id, None)


@router.post("/webhook/sepay")
async def sepay_webhook(request: Request):
    body = await request.body()

    if config.SEPAY_WEBHOOK_SECRET:
        sig = request.headers.get("X-SePay-Signature", "")
        expected = hmac.new(
            config.SEPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    tx_id = str(payload.get("id") or payload.get("referenceCode", ""))

    if tx_id and sheets.transaction_exists(tx_id):
        return {"status": "duplicate", "tx_id": tx_id}

    amount = float(payload.get("transferAmount", 0))
    transfer_type = payload.get("transferType", "in")
    content = payload.get("content", "")
    gateway = payload.get("gateway", "")
    tx_date_str = payload.get("transactionDate", "")

    try:
        tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        tx_date = datetime.now()

    tx_type = "income" if transfer_type == "in" else "expense"

    tx_data = {
        "tx_id": tx_id,
        "amount": amount,
        "tx_type": tx_type,
        "content": content,
        "gateway": gateway,
        "tx_date": tx_date,
    }
    _pending_transactions[tx_id] = tx_data

    if _discord_bot:
        channel = _discord_bot.get_channel(config.DISCORD_CHANNEL_ID)
        if channel:
            direction = "💚 Tiền vào" if tx_type == "income" else "🔴 Tiền ra"
            from handlers.views import OwnerSelectView
            msg = (
                f"{direction} **{amount:,.0f}đ** · {gateway}\n"
                f"📝 `{content}`\n"
                f"🕐 {tx_date.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Khoản này dùng cho ai?"
            )
            view = OwnerSelectView(tx_data)
            await channel.send(msg, view=view)

    return {"status": "ok", "tx_id": tx_id}