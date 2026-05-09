"""
Google Sheets service.
Cấu trúc spreadsheet:
  Sheet "Transactions": Date | Amount | Type | Category | Description | Source | TX_ID
  Sheet "Budget":       Category | Monthly Limit | Note
  Sheet "Config":       Key | Value
"""

from __future__ import annotations

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Optional
import config


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_client: Optional[gspread.Client] = None
_spreadsheet: Optional[gspread.Spreadsheet] = None


def _get_spreadsheet() -> gspread.Spreadsheet:
    global _client, _spreadsheet
    if _spreadsheet is None:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=SCOPES
        )
        _client = gspread.authorize(creds)
        _spreadsheet = _client.open_by_key(config.SPREADSHEET_ID)
        _ensure_sheets()
    return _spreadsheet


def _ensure_sheets():
    """Tạo các sheet cần thiết nếu chưa có."""
    ss = _spreadsheet
    existing = [ws.title for ws in ss.worksheets()]

    if config.SHEET_TRANSACTIONS not in existing:
        ws = ss.add_worksheet(config.SHEET_TRANSACTIONS, rows=1000, cols=7)
        ws.append_row(["Date", "Amount", "Type", "Category", "Description", "Source", "TX_ID"])

    if config.SHEET_BUDGET not in existing:
        ws = ss.add_worksheet(config.SHEET_BUDGET, rows=50, cols=3)
        ws.append_row(["Category", "Monthly Limit", "Note"])
        # Populate đúng format 2 tầng: "👤 Cá nhân › 🍜 Ăn uống"
        for owner, cats in config.CATEGORY_TREE.items():
            for cat in cats:
                ws.append_row([f"{owner} › {cat}", 0, ""])

    if config.SHEET_CONFIG not in existing:
        ws = ss.add_worksheet(config.SHEET_CONFIG, rows=20, cols=2)
        ws.append_row(["Key", "Value"])


def reset_budget_sheet():
    """Xóa và populate lại Budget sheet với category 2 tầng."""
    ss = _get_spreadsheet()
    ws = ss.worksheet(config.SHEET_BUDGET)
    ws.clear()
    ws.append_row(["Category", "Monthly Limit", "Note"])
    rows = []
    for owner, cats in config.CATEGORY_TREE.items():
        for cat in cats:
            rows.append([f"{owner} › {cat}", 0, ""])
    ws.append_rows(rows)


# ── Transactions ──────────────────────────────────────────────────────────────

def add_transaction(
    amount: float,
    tx_type: str,
    category: str,
    description: str,
    source: str = "manual",
    tx_id: str = "",
    date: Optional[datetime] = None,
) -> None:
    ss = _get_spreadsheet()
    ws = ss.worksheet(config.SHEET_TRANSACTIONS)
    dt = (date or datetime.now()).strftime("%Y-%m-%d %H:%M")
    ws.append_row([dt, amount, tx_type, category, description, source, tx_id])


def get_transactions(month: Optional[str] = None) -> list[dict]:
    ss = _get_spreadsheet()
    ws = ss.worksheet(config.SHEET_TRANSACTIONS)
    rows = ws.get_all_records()
    if month:
        rows = [r for r in rows if str(r.get("Date", "")).startswith(month)]
    return rows


def transaction_exists(tx_id: str) -> bool:
    if not tx_id:
        return False
    ss = _get_spreadsheet()
    ws = ss.worksheet(config.SHEET_TRANSACTIONS)
    col = ws.col_values(7)
    return tx_id in col


# ── Budget ────────────────────────────────────────────────────────────────────

def get_budgets() -> list[dict]:
    ss = _get_spreadsheet()
    ws = ss.worksheet(config.SHEET_BUDGET)
    return ws.get_all_records()


def set_budget(category: str, limit: float) -> bool:
    ss = _get_spreadsheet()
    ws = ss.worksheet(config.SHEET_BUDGET)
    rows = ws.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        if row[0].strip() == category.strip():
            ws.update_cell(i, 2, limit)
            return True
    ws.append_row([category, limit, ""])
    return True


def get_monthly_spending(month: str) -> dict[str, float]:
    """Tổng chi theo danh mục trong tháng."""
    txs = get_transactions(month)
    totals: dict[str, float] = {}
    for tx in txs:
        if str(tx.get("Type", "")).lower() == "expense":
            cat = tx.get("Category", "❓ Khác")
            totals[cat] = totals.get(cat, 0) + float(tx.get("Amount", 0))
    return totals


def get_monthly_spending_by_owner(month: str) -> dict[str, dict[str, float]]:
    """
    Tổng chi nhóm theo owner (Cá nhân / Gia đình).
    Trả về: {"👤 Cá nhân": {"🍜 Ăn uống": 150000, ...}, "🏠 Gia đình": {...}}
    """
    spending = get_monthly_spending(month)
    result: dict[str, dict[str, float]] = {}
    for full_cat, amt in spending.items():
        if " › " in full_cat:
            owner, cat = full_cat.split(" › ", 1)
        else:
            owner, cat = "❓ Khác", full_cat
        if owner not in result:
            result[owner] = {}
        result[owner][cat] = result[owner].get(cat, 0) + amt
    return result


def get_monthly_income(month: str) -> float:
    txs = get_transactions(month)
    return sum(float(t.get("Amount", 0)) for t in txs if str(t.get("Type", "")).lower() == "income")


# ── Config ────────────────────────────────────────────────────────────────────

def get_config(key: str, default: str = "") -> str:
    ss = _get_spreadsheet()
    ws = ss.worksheet(config.SHEET_CONFIG)
    rows = ws.get_all_records()
    for row in rows:
        if row.get("Key") == key:
            return str(row.get("Value", default))
    return default


def set_config(key: str, value: str) -> None:
    ss = _get_spreadsheet()
    ws = ss.worksheet(config.SHEET_CONFIG)
    rows = ws.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        if row[0] == key:
            ws.update_cell(i, 2, value)
            return
    ws.append_row([key, value])