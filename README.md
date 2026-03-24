# 💰 SpendWise — Expense Tracker PWA

A production-ready Progressive Web App for tracking personal finances. Built with Flask (Python), SQLite, Chart.js, and a full PWA setup including offline support and push notifications.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Credit & Debit Tracking** | Running balance = total credit − total debit |
| **Dashboard Analytics** | Pie chart, line chart, monthly bar chart |
| **Transaction Management** | Add, edit, delete with categories |
| **CSV Export** | Filter by month/year |
| **PWA** | Installable, offline-capable, Add to Home Screen |
| **Push Notifications** | Daily 8 PM expense reminder |
| **Bank Sync** | Mock provider + pluggable architecture |
| **CSV Import** | Auto-parse Nigerian bank statements |
| **Auto-categorize** | Keyword matching on descriptions |
| **Duplicate Detection** | Prevents re-importing same transactions |
| **Authentication** | Session-based with hashed passwords |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo>
cd expense_tracker

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Run

```bash
python run.py
```

Open **http://localhost:5000** — sign up and you're ready.

### 4. Seed Demo Data (Optional)

```bash
# After creating your account:
python seed_data.py --email your@email.com
```

---

## 🔔 Push Notifications Setup

Push notifications require VAPID keys and HTTPS.

```bash
# Generate VAPID keys
python generate_vapid.py

# Add to .env:
VAPID_PUBLIC_KEY=<output>
VAPID_PRIVATE_KEY=<output>
```

For local testing, use ngrok or Cloudflare Tunnel (HTTPS required for push API).

---

## 🏦 Bank Integration

The app ships with a **Mock Bank Provider** for demo/testing. To add a real bank:

```python
# app/services/bank_sync.py

class MonoProvider(BankProvider):
    def fetch_transactions(self, user_id, days=30):
        # Call Mono API: https://mono.co/docs
        ...

    def fetch_balance(self, user_id):
        ...

# Register it:
PROVIDERS = {
    'mock': MockBankProvider,
    'mono': MonoProvider,
}
```

### Supported Future Providers
- **Mono** (Nigeria) — https://mono.co
- **Stitch** (Africa) — https://stitch.money
- **Plaid** (US/Global) — https://plaid.com

### CSV Import Format

The CSV importer auto-detects columns. Supported headers:

| Column | Aliases |
|---|---|
| Amount | `amount`, `value`, `naira amount` |
| Type | `type`, `cr/dr`, `debit/credit` |
| Description | `description`, `narration`, `remarks` |
| Date | `date`, `transaction date`, `value date` |
| Debit | `debit`, `withdrawal` |
| Credit | `credit`, `deposit` |

---

## 🗄️ Database

**Development:** SQLite (auto-created at `instance/expenses.db`)

**Production:** Set `DATABASE_URL` in `.env`:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/spendwise
```

Install psycopg2:
```bash
pip install psycopg2-binary
```

---

## 🚀 Deployment

### Option 1: Cloudflare Tunnel (recommended for home server)

```bash
# Install cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

cloudflared tunnel --url http://localhost:5000
```

### Option 2: Gunicorn + Nginx

```bash
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

Nginx config:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 3: Railway / Render / Fly.io

```bash
# Railway
railway login
railway new
railway up
```

Set environment variables in the platform dashboard.

---

## 📁 Project Structure

```
expense_tracker/
├── run.py                   # Entry point
├── requirements.txt
├── .env.example
├── generate_vapid.py        # VAPID key generator
├── seed_data.py             # Demo data seeder
├── app/
│   ├── __init__.py          # App factory
│   ├── models.py            # SQLAlchemy models
│   ├── routes.py            # All routes & API endpoints
│   └── services/
│       └── bank_sync.py     # Bank provider architecture
├── templates/
│   ├── base.html
│   ├── auth.html            # Login / Signup
│   ├── dashboard.html       # Analytics dashboard
│   ├── transactions.html    # Transaction list
│   ├── settings.html        # Settings panel
│   └── partials/
│       ├── nav.html
│       └── txn-modal.html
├── static/
│   ├── css/main.css         # Dark theme responsive CSS
│   ├── js/
│   │   ├── utils.js         # Shared helpers
│   │   ├── dashboard.js     # Dashboard charts
│   │   ├── transactions.js  # Transaction list
│   │   └── settings.js      # Settings logic
│   ├── manifest.json        # PWA manifest
│   ├── service-worker.js    # Offline + push notifications
│   └── icons/               # PWA icons (all sizes)
└── instance/
    └── expenses.db          # SQLite database (auto-created)
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/signup` | Create account |
| POST | `/login` | Authenticate |
| POST | `/logout` | Sign out |
| GET | `/user/me` | Current user info |
| GET | `/categories` | List categories |
| POST | `/categories` | Create category |
| GET | `/transactions` | List (paginated, filtered) |
| POST | `/transactions` | Create transaction |
| PUT | `/transactions/<id>` | Update transaction |
| DELETE | `/transactions/<id>` | Delete transaction |
| GET | `/dashboard/data` | Analytics data |
| GET | `/export/csv` | Export CSV |
| POST | `/bank/sync` | Sync from bank provider |
| POST | `/upload/csv` | Import bank statement CSV |
| POST | `/push/subscribe` | Save push subscription |
| POST | `/push/unsubscribe` | Remove push subscription |
| GET | `/push/vapid-public-key` | Get VAPID public key |

---

## 🔐 Security Notes

- Passwords hashed with Werkzeug's `generate_password_hash` (PBKDF2-SHA256)
- Sessions are server-side via Flask-Login
- Change `SECRET_KEY` in production
- Use HTTPS in production (required for PWA + Web Push)
- Never commit `.env` to version control

---

## 🧠 Smart Features

- **Auto-categorization:** Transactions are automatically assigned categories based on keywords in the description (e.g., "Uber" → Transport, "Netflix" → Entertainment)
- **Duplicate detection:** Bank sync and CSV imports skip transactions already in the database (by external ID or amount+date matching)
- **Extensible categories:** Add custom categories per user with custom icons and colors

---

## 📱 PWA Installation

1. Open the app in Chrome/Safari on mobile
2. Tap **Share → Add to Home Screen** (iOS) or the **Install** prompt (Android/Chrome)
3. The app launches fullscreen like a native app

---

## 🛠️ Tech Stack

- **Backend:** Flask 3, Flask-SQLAlchemy, Flask-Login
- **Database:** SQLite / PostgreSQL
- **Frontend:** Vanilla JS, CSS Custom Properties
- **Charts:** Chart.js 4
- **Fonts:** Syne (display) + DM Sans (body) via Google Fonts
- **PWA:** Service Worker API, Web Push API, Web App Manifest
- **Push:** pywebpush + VAPID keys
