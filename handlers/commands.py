"""
Discord slash commands:
  /today                                   — thống kê hôm nay
  /thismonth                               — thống kê tháng này
  /thisyear                                — thống kê năm nay theo từng tháng
  /write <tx_id> <category> <description>  — ghi nhận giao dịch chờ phân loại
  /add <amount> <type> <category> <desc>   — thêm giao dịch thủ công
  /day [YYYY-MM-DD]                        — tóm tắt ngày cụ thể
  /month [YYYY-MM]                         — báo cáo tháng cụ thể
  /summarize                               — tóm tắt tháng hiện tại kèm ngân sách
  /budget set <category> <amount>          — đặt ngân sách
  /budget check                            — kiểm tra tình trạng ngân sách
  /categories                              — liệt kê danh mục
"""

from __future__ import annotations

import discord
from discord import app_commands
from datetime import datetime, date
from typing import Optional

import config
from services import sheets, budget as budget_svc
from handlers.webhook import get_pending, remove_pending


# ── Helpers ────────────────────────────────────────────────────────────────────

def _format_day_report(target: str, txs: list[dict]) -> str:
    total_in  = sum(float(t["Amount"]) for t in txs if t.get("Type") == "income")
    total_out = sum(float(t["Amount"]) for t in txs if t.get("Type") == "expense")

    by_cat: dict[str, float] = {}
    for t in txs:
        if t.get("Type") == "expense":
            cat = t.get("Category", "❓ Khác")
            by_cat[cat] = by_cat.get(cat, 0) + float(t.get("Amount", 0))

    lines = [
        f"📅 **Ngày {target}**",
        f"━━━━━━━━━━━━━━━━━━",
        f"💚 Thu:  **{total_in:,.0f}đ**",
        f"🔴 Chi:  **{total_out:,.0f}đ**",
        f"📈 Còn:  **{total_in - total_out:,.0f}đ**",
    ]
    if by_cat:
        lines.append(f"━━━━━━━━━━━━━━━━━━")
        lines.append("**Chi theo danh mục:**")
        for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
            lines.append(f"  • {cat}: **{amt:,.0f}đ**")
    lines.append(f"━━━━━━━━━━━━━━━━━━")
    lines.append("**Giao dịch:**")
    for t in txs:
        icon = "💚" if t.get("Type") == "income" else "🔴"
        lines.append(f"{icon} {float(t['Amount']):,.0f}đ — {t.get('Category')} — {t.get('Description')}")
    return "\n".join(lines)


def _format_month_report(target: str, label: str = "") -> str:
    txs = sheets.get_transactions(target)
    if not txs:
        return f"📭 Không có giao dịch nào {'tháng ' + target if not label else label}."

    spending = sheets.get_monthly_spending(target)
    income   = sheets.get_monthly_income(target)
    total_out = sum(spending.values())

    title = label or f"Tháng {target}"
    lines = [
        f"📊 **{title}**",
        f"━━━━━━━━━━━━━━━━━━",
        f"💚 Thu nhập:  **{income:,.0f}đ**",
        f"🔴 Chi tiêu:  **{total_out:,.0f}đ**",
        f"📈 Còn lại:   **{income - total_out:,.0f}đ**",
        f"━━━━━━━━━━━━━━━━━━",
        "**Chi theo danh mục:**",
    ]
    for cat, amt in sorted(spending.items(), key=lambda x: -x[1]):
        lines.append(f"  • {cat}: **{amt:,.0f}đ**")
    return "\n".join(lines)


# ── Commands setup ─────────────────────────────────────────────────────────────

def setup_commands(bot: discord.Client, tree: app_commands.CommandTree):

    # ── /today ─────────────────────────────────────────────────────────────────
    @tree.command(name="today", description="Thống kê chi tiêu hôm nay")
    async def cmd_today(interaction: discord.Interaction):
        await interaction.response.defer()
        today = date.today().isoformat()
        month = today[:7]
        txs = [t for t in sheets.get_transactions(month) if str(t.get("Date", "")).startswith(today)]
        if not txs:
            await interaction.followup.send(f"📭 Hôm nay ({today}) chưa có giao dịch nào.")
            return
        await interaction.followup.send(_format_day_report(today, txs))

    # ── /thismonth ─────────────────────────────────────────────────────────────
    @tree.command(name="thismonth", description="Thống kê chi tiêu tháng này")
    async def cmd_thismonth(interaction: discord.Interaction):
        await interaction.response.defer()
        month = datetime.now().strftime("%Y-%m")
        await interaction.followup.send(_format_month_report(month, f"Tháng {month}"))

    # ── /thisyear ──────────────────────────────────────────────────────────────
    @tree.command(name="thisyear", description="Thống kê chi tiêu năm nay theo từng tháng")
    async def cmd_thisyear(interaction: discord.Interaction):
        await interaction.response.defer()
        year = datetime.now().year
        now_month = datetime.now().month

        yearly_income  = 0.0
        yearly_expense = 0.0
        monthly_rows   = []

        for m in range(1, now_month + 1):
            month_str = f"{year}-{m:02d}"
            txs = sheets.get_transactions(month_str)
            if not txs:
                continue
            inc = sum(float(t["Amount"]) for t in txs if t.get("Type") == "income")
            exp = sum(float(t["Amount"]) for t in txs if t.get("Type") == "expense")
            yearly_income  += inc
            yearly_expense += exp
            monthly_rows.append((month_str, inc, exp))

        if not monthly_rows:
            await interaction.followup.send(f"📭 Năm {year} chưa có giao dịch nào.")
            return

        lines = [
            f"📆 **Thống kê năm {year}**",
            f"━━━━━━━━━━━━━━━━━━",
            f"💚 Tổng thu:  **{yearly_income:,.0f}đ**",
            f"🔴 Tổng chi:  **{yearly_expense:,.0f}đ**",
            f"📈 Tiết kiệm: **{yearly_income - yearly_expense:,.0f}đ**",
            f"━━━━━━━━━━━━━━━━━━",
            "**Chi tiết từng tháng:**",
        ]
        for month_str, inc, exp in monthly_rows:
            balance = inc - exp
            sign    = "+" if balance >= 0 else ""
            lines.append(
                f"  `{month_str}` — Thu: {inc:,.0f}đ  Chi: {exp:,.0f}đ  "
                f"({sign}{balance:,.0f}đ)"
            )

        await interaction.followup.send("\n".join(lines))

    # ── /write ─────────────────────────────────────────────────────────────────
    @tree.command(name="write", description="Phân loại giao dịch ngân hàng vừa phát sinh")
    @app_commands.describe(
        tx_id="ID giao dịch (lấy từ thông báo)",
        category="Danh mục chi tiêu",
        description="Mô tả ngắn gọn",
    )
    async def cmd_write(interaction: discord.Interaction, tx_id: str, category: str, description: str):
        await interaction.response.defer()
        pending = get_pending(tx_id)
        if not pending:
            await interaction.followup.send(f"❌ Không tìm thấy giao dịch `{tx_id}`. Có thể đã được ghi rồi.")
            return

        sheets.add_transaction(
            amount=pending["amount"],
            tx_type=pending["tx_type"],
            category=category,
            description=description,
            source=pending.get("gateway", "sepay"),
            tx_id=tx_id,
            date=pending.get("tx_date"),
        )
        remove_pending(tx_id)

        month = datetime.now().strftime("%Y-%m")
        alerts = budget_svc.check_budget_alerts(month)
        cat_alerts = [a for a in alerts if a["category"] == category]

        reply = f"✅ Đã ghi: **{pending['amount']:,.0f}đ** — {category}\n📝 {description}"
        if cat_alerts:
            reply += "\n\n" + budget_svc.format_alert_message(cat_alerts[0])
        await interaction.followup.send(reply)

    # ── /add ───────────────────────────────────────────────────────────────────
    @tree.command(name="add", description="Thêm giao dịch thủ công")
    @app_commands.describe(
        amount="Số tiền (VND)",
        tx_type="Loại: income hoặc expense",
        category="Danh mục",
        description="Mô tả",
    )
    async def cmd_add(interaction: discord.Interaction, amount: float, tx_type: str, category: str, description: str):
        await interaction.response.defer()
        if tx_type not in ("income", "expense"):
            await interaction.followup.send("❌ `type` phải là `income` hoặc `expense`.")
            return

        sheets.add_transaction(amount=amount, tx_type=tx_type, category=category, description=description, source="manual")

        icon = "💚" if tx_type == "income" else "🔴"
        alerts = budget_svc.check_budget_alerts()
        cat_alerts = [a for a in alerts if a["category"] == category]

        reply = f"{icon} Đã ghi: **{amount:,.0f}đ** — {category}\n📝 {description}"
        if cat_alerts:
            reply += "\n\n" + budget_svc.format_alert_message(cat_alerts[0])
        await interaction.followup.send(reply)

    # ── /day ───────────────────────────────────────────────────────────────────
    @tree.command(name="day", description="Tóm tắt chi tiêu ngày cụ thể (YYYY-MM-DD)")
    @app_commands.describe(day="Ngày cần xem, ví dụ: 2024-01-15")
    async def cmd_day(interaction: discord.Interaction, day: str):
        await interaction.response.defer()
        month = day[:7]
        txs = [t for t in sheets.get_transactions(month) if str(t.get("Date", "")).startswith(day)]
        if not txs:
            await interaction.followup.send(f"📭 Không có giao dịch nào ngày {day}.")
            return
        await interaction.followup.send(_format_day_report(day, txs))

    # ── /month ─────────────────────────────────────────────────────────────────
    @tree.command(name="month", description="Báo cáo chi tiêu tháng cụ thể (YYYY-MM)")
    @app_commands.describe(month="Tháng cần xem, ví dụ: 2024-01")
    async def cmd_month(interaction: discord.Interaction, month: str):
        await interaction.response.defer()
        await interaction.followup.send(_format_month_report(month))

    # ── /summarize ─────────────────────────────────────────────────────────────
    @tree.command(name="summarize", description="Tóm tắt tháng này kèm tình trạng ngân sách")
    async def cmd_summarize(interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(budget_svc.build_budget_summary())

    # ── /budget ────────────────────────────────────────────────────────────────
    budget_group = app_commands.Group(name="budget", description="Quản lý ngân sách theo danh mục")

    @budget_group.command(name="set", description="Đặt ngân sách cho 1 danh mục")
    @app_commands.describe(category="Tên danh mục", amount="Hạn mức (VND/tháng)")
    async def budget_set(interaction: discord.Interaction, category: str, amount: float):
        await interaction.response.defer()
        sheets.set_budget(category, amount)
        await interaction.followup.send(f"✅ Đã đặt ngân sách **{category}**: {amount:,.0f}đ/tháng.")

    @budget_group.command(name="check", description="Kiểm tra tình trạng ngân sách tháng này")
    async def budget_check(interaction: discord.Interaction):
        await interaction.response.defer()
        alerts = budget_svc.check_budget_alerts()
        if not alerts:
            await interaction.followup.send("✅ Tất cả danh mục đều trong ngân sách cho phép.")
            return
        await interaction.followup.send("\n\n".join(budget_svc.format_alert_message(a) for a in alerts))

    tree.add_command(budget_group)

    # ── /categories ────────────────────────────────────────────────────────────
    @tree.command(name="categories", description="Xem danh sách danh mục chi tiêu")
    async def cmd_categories(interaction: discord.Interaction):
        lines = ["**Danh mục chi tiêu:**"]
        for owner, cats in config.CATEGORY_TREE.items():
            lines.append(f"\n**{owner}**")
            for cat in cats:
                lines.append(f"  • `{cat}`")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)