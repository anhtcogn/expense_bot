# 💰 Personal Expense Bot

Bot Discord quản lý chi tiêu cá nhân, tự động phát hiện giao dịch ngân hàng qua SePay, phân loại bằng button Discord và lưu vào Google Sheets.

## Kiến trúc

```
Ngân hàng → SePay Webhook → FastAPI Server
                                  ↓
                         Discord (button chọn danh mục)
                                  ↓
                          Google Sheets (lưu trữ)
                                  ↓
                       Scheduler (báo cáo 22:00 hàng ngày)
```

## Cách dùng

### Khi có giao dịch ngân hàng

Bot tự động gửi vào Discord kèm button chọn 2 tầng:

```
🔴 Tiền ra 150,000đ · VCB
📝 `GRAB FOOD 123456`
🕐 15/01/2024 14:30

Khoản này dùng cho ai?
[👤 Cá nhân]  [🏠 Gia đình]
```

Sau khi click **👤 Cá nhân**, bot gửi tiếp dropdown chọn danh mục:

```
✅ 👤 Cá nhân — Chọn danh mục chi tiêu:
[Dropdown: 🍜 Ăn uống / 🎮 Giải trí / 👗 Quần áo ...]
```

Sau khi chọn xong, bot confirm và hiển thị tổng chi trong ngày:

```
✅ Đã ghi giao dịch
━━━━━━━━━━━━━━━━━━
💸 Số tiền: 150,000đ
🗂️ Danh mục: 👤 Cá nhân › 🍜 Ăn uống
📝 GRAB FOOD 123456
━━━━━━━━━━━━━━━━━━
📅 Tổng chi hôm nay: 350,000đ
```

### Slash Commands

| Command | Mô tả |
|---------|-------|
| `/today` | Thống kê chi tiêu hôm nay |
| `/thismonth` | Thống kê tháng này |
| `/thisyear` | Thống kê năm nay theo từng tháng |
| `/day <YYYY-MM-DD>` | Chi tiêu ngày cụ thể |
| `/month <YYYY-MM>` | Báo cáo tháng cụ thể |
| `/summarize` | Tóm tắt tháng + tình trạng ngân sách |
| `/add <amount> <type> <category> <desc>` | Thêm giao dịch thủ công |
| `/write <tx_id> <category> <desc>` | Phân loại giao dịch thủ công (fallback) |
| `/budget set <category> <amount>` | Đặt ngân sách cho danh mục |
| `/budget check` | Kiểm tra cảnh báo ngân sách |
| `/categories` | Xem danh sách danh mục |

### Báo cáo tự động

M��i ngày lúc **22:00**, bot tự động gửi tổng kết chi tiêu trong ngày vào channel, bao gồm tổng thu/chi, breakdown theo danh mục và cảnh báo ngân sách nếu có.

### Danh mục chi tiêu (2 tầng)

**👤 Cá nhân:** 🍜 Ăn uống · 🎮 Giải trí · 👗 Quần áo · 💊 Sức khoẻ · 📚 Học tập · 🚗 Di chuyển · 💼 Công việc · ❓ Khác

**🏠 Gia đình:** 🛒 Đồ dùng gia đình · 🍚 Thực phẩm · 💡 Hoá đơn / tiện ích · 🏥 Y tế · 🎒 Con cái · 🔧 Sửa chữa · ❓ Khác

---

## Cài đặt & Deploy

### Bước 1 — Tạo Discord Bot

1. Vào [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application**
2. Tab **Bot** → **Reset Token** → copy token
3. Bật **Privileged Gateway Intents**: `Message Content Intent`
4. **OAuth2 → URL Generator**: tích `bot` + `applications.commands`
   Permissions: `Send Messages`, `Read Message History`, `Use Slash Commands`
5. Mở link invite để thêm bot vào server

Lấy `DISCORD_CHANNEL_ID`: bật Developer Mode trong Discord → chuột phải channel → **Copy Channel ID**

### Bước 2 — Google Sheets API

1. Vào [console.cloud.google.com](https://console.cloud.google.com) → tạo project mới
2. Enable **Google Sheets API** và **Google Drive API**
3. **IAM → Service Accounts** → Create → tạo key JSON → download
4. Tạo Google Spreadsheet mới → copy ID từ URL
   (`docs.google.com/spreadsheets/d/**ID_HERE**/edit`)
5. Share spreadsheet với email của service account (quyền **Editor**)

### Bước 3 — SePay

1. Đăng ký tại [sepay.vn](https://sepay.vn) → liên kết tài khoản ngân hàng
2. Vào **Webhook** → điền URL (cập nhật sau khi có Railway URL ở bước 4)
3. Copy **Webhook Secret**

### Bước 4 — Deploy lên Railway

#### 4.1 Push code lên GitHub

Tạo file `.gitignore`:

```
.env
credentials.json
__pycache__/
*.pyc
.venv/
```

Tạo file `Procfile` (Railway dùng để biết lệnh chạy):

```
worker: python main.py
```

Push lên GitHub:

```bash
git init
git add .
git commit -m "init expense bot"
git remote add origin https://github.com/your-username/expense-bot.git
git push -u origin main
```

#### 4.2 Tạo project trên Railway

1. Vào [railway.app](https://railway.app) → **Login with GitHub**
2. **New Project** → **Deploy from GitHub repo** → chọn repo
3. Railway tự động build và deploy

#### 4.3 Thêm Environment Variables

Tab **Variables** trong Railway dashboard → thêm từng biến:

```
DISCORD_BOT_TOKEN        = your_token
DISCORD_CHANNEL_ID       = your_channel_id
DISCORD_GUILD_ID         = your_guild_id
SEPAY_WEBHOOK_SECRET     = your_secret
SPREADSHEET_ID           = your_spreadsheet_id
WEBHOOK_PORT             = 8000
```

#### 4.4 Upload credentials.json

File JSON của Google không để vào repo được. Encode thành base64:

```bash
# macOS / Linux
base64 -i credentials.json

# Windows (PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("credentials.json"))
```

Copy toàn bộ output, thêm vào Railway:

```
GOOGLE_CREDENTIALS_BASE64 = <chuỗi base64>
```

Thêm đoạn sau vào đầu `config.py` để tự decode khi chạy:

```python
import base64, tempfile

_b64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
if _b64:
    _tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    _tmp.write(base64.b64decode(_b64))
    _tmp.close()
    GOOGLE_SERVICE_ACCOUNT_JSON = _tmp.name
else:
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
```

Commit và push lên GitHub — Railway sẽ tự redeploy.

#### 4.5 Lấy URL webhook

Tab **Settings** → **Networking** → **Generate Domain** → Railway cấp URL dạng:

```
https://expense-bot-xxxx.railway.app
```

Quay lại SePay → điền webhook URL:

```
https://expense-bot-xxxx.railway.app/webhook/sepay
```

#### 4.6 Kiểm tra

Tab **Logs** trong Railway phải hiện:

```
Discord bot logged in as ExpenseBot#1234
Synced 8 slash commands
Scheduler started
```

Gõ `/today` trong Discord để test — nếu bot phản hồi là xong.

---

### Chạy local (để dev/test)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Điền thông tin vào .env, để credentials.json cùng thư mục
python main.py
```

Dùng ngrok để test SePay webhook local:

```bash
ngrok http 8000
# Điền URL ngrok vào SePay webhook settings
```

---

## Cấu trúc Google Sheets

**Sheet "Transactions"**
| Date | Amount | Type | Category | Description | Source | TX_ID |
|------|--------|------|----------|-------------|--------|-------|

**Sheet "Budget"**
| Category | Monthly Limit | Note |
|----------|---------------|------|

**Sheet "Config"**
| Key | Value |
|-----|-------|

---

## Cấu trúc project

```
expense_bot/
├── main.py                  # Entry point
├── config.py                # Env vars + cấu hình danh mục
├── Procfile                 # Railway process config
├── requirements.txt
├── .env.example
├── services/
│   ├── sheets.py            # Đọc/ghi Google Sheets
│   └── budget.py            # Logic ngân sách & cảnh báo
└── handlers/
    ├── webhook.py           # FastAPI endpoint nhận SePay
    ├── views.py             # Discord UI buttons & select menus
    ├── commands.py          # Slash commands
    └── scheduler.py        # Báo cáo tự động 22:00
```