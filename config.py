import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

SEPAY_WEBHOOK_SECRET = os.getenv("SEPAY_WEBHOOK_SECRET", "")

GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8000"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")

# Google Sheets tab names
SHEET_TRANSACTIONS = "Transactions"
SHEET_BUDGET = "Budget"
SHEET_CONFIG = "Config"

# Danh mục chi tiêu mặc định
DEFAULT_CATEGORIES = [
    "🍜 Ăn uống",
    "🏠 Nhà cửa",
    "🚗 Di chuyển",
    "🛍️ Mua sắm",
    "💊 Sức khoẻ",
    "🎮 Giải trí",
    "📚 Học tập",
    "💼 Công việc",
    "💰 Thu nhập",
    "🔄 Chuyển khoản",
    "❓ Khác",
]

# Ngưỡng cảnh báo ngân sách (%)
BUDGET_WARNING_THRESHOLD = 80   # cảnh báo khi đã dùng 80%
BUDGET_DANGER_THRESHOLD = 95    # cảnh báo nguy hiểm khi dùng 95%