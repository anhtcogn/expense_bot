"""
Budget service: kiểm tra ngân sách và tạo cảnh báo.
"""

from __future__ import annotations
from datetime import datetime
from services import sheets
import config


def check_budget_alerts(month: str | None = None) -> list[dict]:
    """
    Kiểm tra tất cả danh mục, trả về list cảnh báo với mức độ warning/danger.
    """
    if month is None:
        month = datetime.now().strftime("%Y-%m")

    budgets = {b["Category"]: float(b.get("Monthly Limit", 0)) for b in sheets.get_budgets()}
    spending = sheets.get_monthly_spending(month)
    alerts = []

    for cat, limit in budgets.items():
        if limit <= 0:
            continue
        spent = spending.get(cat, 0)
        pct = (spent / limit) * 100
        if pct >= config.BUDGET_DANGER_THRESHOLD:
            alerts.append({
                "category": cat,
                "limit": limit,
                "spent": spent,
                "percent": pct,
                "level": "danger",
            })
        elif pct >= config.BUDGET_WARNING_THRESHOLD:
            alerts.append({
                "category": cat,
                "limit": limit,
                "spent": spent,
                "percent": pct,
                "level": "warning",
            })

    return alerts


def format_alert_message(alert: dict) -> str:
    emoji = "🚨" if alert["level"] == "danger" else "⚠️"
    remaining = alert["limit"] - alert["spent"]
    return (
        f"{emoji} **Cảnh báo ngân sách** — {alert['category']}\n"
        f"Đã dùng: **{alert['spent']:,.0f}đ** / {alert['limit']:,.0f}đ "
        f"({alert['percent']:.0f}%)\n"
        f"Còn lại: **{max(remaining, 0):,.0f}đ**"
    )


def build_budget_summary(month: str | None = None) -> str:
    """Tóm tắt toàn bộ ngân sách tháng theo dạng text."""
    if month is None:
        month = datetime.now().strftime("%Y-%m")

    budgets = {b["Category"]: float(b.get("Monthly Limit", 0)) for b in sheets.get_budgets()}
    spending = sheets.get_monthly_spending(month)
    income = sheets.get_monthly_income(month)
    total_expense = sum(spending.values())

    lines = [f"📊 **Báo cáo ngân sách tháng {month}**\n"]
    lines.append(f"💰 Thu nhập: **{income:,.0f}đ**")
    lines.append(f"💸 Tổng chi: **{total_expense:,.0f}đ**")
    lines.append(f"📈 Tiết kiệm: **{income - total_expense:,.0f}đ**\n")
    lines.append("**Chi tiết theo danh mục:**")

    for cat, limit in budgets.items():
        spent = spending.get(cat, 0)
        if spent == 0 and limit == 0:
            continue
        if limit > 0:
            pct = (spent / limit) * 100
            bar = _progress_bar(pct)
            status = "🚨" if pct >= 95 else "⚠️" if pct >= 80 else "✅"
            lines.append(f"{status} {cat}: {spent:,.0f}đ / {limit:,.0f}đ {bar} {pct:.0f}%")
        else:
            lines.append(f"📌 {cat}: {spent:,.0f}đ (chưa đặt ngân sách)")

    # Danh mục có chi nhưng chưa set budget
    for cat, spent in spending.items():
        if cat not in budgets and spent > 0:
            lines.append(f"📌 {cat}: {spent:,.0f}đ (chưa đặt ngân sách)")

    return "\n".join(lines)


def _progress_bar(pct: float, length: int = 8) -> str:
    filled = min(int(pct / 100 * length), length)
    return "[" + "█" * filled + "░" * (length - filled) + "]"