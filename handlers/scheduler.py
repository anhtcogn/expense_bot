"""
Scheduler: chỉ 1 job duy nhất — báo cáo tổng chi tiêu cuối ngày lúc 22:00.
"""

from __future__ import annotations

from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import discord as discord_lib

import config
from services import sheets, budget as budget_svc

_scheduler = AsyncIOScheduler()


def start(bot: discord_lib.Client):
    _scheduler.add_job(
        _daily_report,
        "cron",
        hour=22,
        minute=0,
        args=[bot],
        id="daily_report",
        replace_existing=True,
    )
    _scheduler.start()


async def _daily_report(bot: discord_lib.Client):
    channel = bot.get_channel(config.DISCORD_CHANNEL_ID)
    if not channel:
        return

    today = date.today().isoformat()
    month = today[:7]
    txs = [
        t for t in sheets.get_transactions(month)
        if str(t.get("Date", "")).startswith(today)
    ]

    if not txs:
        await channel.send(
            f"🌙 **Báo cáo ngày {today}**\n"
            f"Hôm nay không có giao dịch nào được ghi nhận."
        )
        return

    income_txs  = [t for t in txs if t.get("Type") == "income"]
    expense_txs = [t for t in txs if t.get("Type") == "expense"]
    total_in  = sum(float(t.get("Amount", 0)) for t in income_txs)
    total_out = sum(float(t.get("Amount", 0)) for t in expense_txs)

    # Gom chi tiêu theo danh mục
    by_cat: dict[str, float] = {}
    for t in expense_txs:
        cat = t.get("Category", "❓ Khác")
        by_cat[cat] = by_cat.get(cat, 0) + float(t.get("Amount", 0))

    lines = [
        f"🌙 **Báo cáo chi tiêu ngày {today}**",
        f"━━━━━━━━━━━━━━━━━━",
        f"💚 Thu nhập:  **{total_in:,.0f}đ**",
        f"🔴 Chi tiêu:  **{total_out:,.0f}đ**",
        f"📈 Còn lại:   **{total_in - total_out:,.0f}đ**",
        f"━━━━━━━━━━━━━━━━━━",
        f"**Chi theo danh mục:**",
    ]

    for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
        lines.append(f"  • {cat}: **{amt:,.0f}đ**")

    # Cảnh báo ngân sách nếu có
    alerts = budget_svc.check_budget_alerts()
    if alerts:
        lines.append(f"\n**⚠️ Cảnh báo ngân sách:**")
        for alert in alerts:
            lines.append(budget_svc.format_alert_message(alert))

    await channel.send("\n".join(lines))