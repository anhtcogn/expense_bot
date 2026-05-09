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

# Cấu trúc 2 tầng: Đối tượng → Danh mục
# Tầng 1: Cá nhân / Gia đình
# Tầng 2: Danh mục chi tiêu theo đối tượng
CATEGORY_TREE = {
    "👤 Cá nhân": [
        "🍜 Ăn uống",
        "🎮 Giải trí",
        "👗 Quần áo",
        "💊 Sức khoẻ",
        "📚 Học tập",
        "🚗 Di chuyển",
        "💼 Công việc",
        "❓ Khác",
    ],
    "🏠 Gia đình": [
        "🛒 Đồ dùng gia đình",
        "🍚 Thực phẩm",
        "💡 Hoá đơn / tiện ích",
        "🏥 Y tế",
        "🎒 Con cái",
        "🔧 Sửa chữa",
        "❓ Khác",
    ],
}

# Flat list để dùng cho báo cáo / budget
DEFAULT_CATEGORIES = [cat for cats in CATEGORY_TREE.values() for cat in cats]

# Ngưỡng cảnh báo ngân sách (%)
BUDGET_WARNING_THRESHOLD = 80
BUDGET_DANGER_THRESHOLD = 95

import base64, tempfile

_b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
if _b64:
    _tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    _tmp.write(base64.b64decode(_b64))
    _tmp.close()
    GOOGLE_SERVICE_ACCOUNT_JSON = _tmp.name
else:
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
