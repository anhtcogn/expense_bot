"""
Discord UI components: Views, Buttons, Select menus cho flow chọn category 2 tầng.

Flow:
  1. Bot gửi message với 2 button: [👤 Cá nhân] [🏠 Gia đình]
  2. User click → bot gửi Select Menu với các danh mục của tầng đó
  3. User chọn danh mục → bot ghi Sheets và gửi confirm
"""

from __future__ import annotations

import logging
import discord
from datetime import datetime, date

import config
from services import sheets
from services import budget as budget_svc

log = logging.getLogger("expense_bot.views")


# ── Tầng 1: Chọn đối tượng (Cá nhân / Gia đình) ──────────────────────────────

class OwnerSelectView(discord.ui.View):
    def __init__(self, tx_data: dict):
        super().__init__(timeout=300)
        self.tx_data = tx_data
        for owner in config.CATEGORY_TREE:
            self.add_item(OwnerButton(owner, tx_data))


class OwnerButton(discord.ui.Button):
    def __init__(self, owner: str, tx_data: dict):
        style = discord.ButtonStyle.primary if "Cá nhân" in owner else discord.ButtonStyle.secondary
        super().__init__(label=owner, style=style)
        self.owner = owner
        self.tx_data = tx_data

    async def callback(self, interaction: discord.Interaction):
        # Defer ngay lập tức — phải trong 3 giây
        await interaction.response.defer()

        categories = config.CATEGORY_TREE[self.owner]

        # Disable tất cả button sau khi chọn
        for item in self.view.children:
            item.disabled = True
            if isinstance(item, OwnerButton) and item.owner == self.owner:
                item.style = discord.ButtonStyle.success

        await interaction.edit_original_response(view=self.view)
        await interaction.followup.send(
            f"✅ **{self.owner}** — Chọn danh mục chi tiêu:",
            view=CategorySelectView(self.tx_data, self.owner, categories),
        )


# ── Tầng 2: Chọn danh mục ────────────────────────────────────────────────────

class CategorySelectView(discord.ui.View):
    def __init__(self, tx_data: dict, owner: str, categories: list[str]):
        super().__init__(timeout=300)
        self.add_item(CategorySelect(tx_data, owner, categories))


class CategorySelect(discord.ui.Select):
    def __init__(self, tx_data: dict, owner: str, categories: list[str]):
        options = [
            discord.SelectOption(label=cat, value=f"{owner}|{cat}")
            for cat in categories
        ]
        super().__init__(placeholder="Chọn danh mục...", options=options, min_values=1, max_values=1)
        self.tx_data = tx_data
        self.owner = owner

    async def callback(self, interaction: discord.Interaction):
        # Defer ngay lập tức trước mọi thứ — tránh 10062 Unknown interaction
        await interaction.response.defer()

        selected = self.values[0]
        owner, category = selected.split("|", 1)
        full_category = f"{owner} › {category}"

        tx = self.tx_data
        amount    = tx["amount"]
        tx_type   = tx["tx_type"]
        tx_id     = tx["tx_id"]
        tx_date   = tx.get("tx_date", datetime.now())
        content   = tx.get("content", "")

        # Ghi vào Google Sheets (có thể chậm — OK vì đã defer rồi)
        try:
            sheets.add_transaction(
                amount=amount,
                tx_type=tx_type,
                category=full_category,
                description=content,
                source=tx.get("gateway", "sepay"),
                tx_id=tx_id,
                date=tx_date,
            )
        except Exception as e:
            log.exception(f"Failed to write to Sheets: {e}")
            await interaction.followup.send(f"❌ Lỗi ghi Google Sheets: `{e}`")
            return

        from handlers.webhook import remove_pending
        remove_pending(tx_id)

        # Tổng chi hôm nay
        today = date.today().isoformat()
        month = today[:7]
        try:
            today_txs = [
                t for t in sheets.get_transactions(month)
                if str(t.get("Date", "")).startswith(today) and t.get("Type") == "expense"
            ]
            today_total = sum(float(t.get("Amount", 0)) for t in today_txs)
        except Exception:
            today_total = amount  # fallback nếu Sheets lỗi

        # Cảnh báo ngân sách
        try:
            alerts = budget_svc.check_budget_alerts()
            cat_alert = next((a for a in alerts if a["category"] == full_category), None)
        except Exception:
            cat_alert = None

        # Disable select sau khi chọn
        self.disabled = True
        self.placeholder = f"✅ {category}"
        await interaction.edit_original_response(view=self.view)

        # Confirm message
        confirm = (
            f"✅ **Đã ghi giao dịch**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💸 Số tiền: **{amount:,.0f}đ**\n"
            f"🗂️ Danh mục: **{full_category}**\n"
            f"📝 Nội dung: {content}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 Tổng chi hôm nay: **{today_total:,.0f}đ**"
        )
        if cat_alert:
            confirm += f"\n\n{budget_svc.format_alert_message(cat_alert)}"

        await interaction.followup.send(confirm)