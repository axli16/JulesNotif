# Jules Notifier

Google Jules sends email notifications when tasks complete, fail, or need review — but email is easy to miss. This project watches your Gmail for those Jules emails, sends an instant push notification to your phone, and cleans up the email so your inbox stays tidy.

## Why

Jules is great at working in the background, but its only notification channel is email. If you're away from your computer or deep in another task, you might not notice a Jules update for hours. This tool bridges that gap by turning every Jules email into a real-time phone notification with status context (✅ completed, ❌ failed, 👀 needs review) so you can act on it immediately.

## Architecture

```
┌─────────────┐       ┌──────────────────┐       ┌──────────┐       ┌──────────┐
│   Gmail     │──────▶│  Python Service   │──────▶│  ntfy.sh │──────▶│  Phone   │
│   Inbox     │◀──────│  (polling loop)   │       │  (push)  │       │  (app)   │
└─────────────┘       └──────────────────┘       └──────────┘       └──────────┘
  Jules emails          parse & cleanup            HTTP POST          notification
```

| Component | Role |
|-----------|------|
| **gmail_client.py** | OAuth2 auth, searches inbox, fetches email content, trashes/archives processed emails |
| **email_parser.py** | Extracts task status, repo name, summary, and links from Jules email HTML |
| **notifier.py** | Sends push notifications via ntfy with priority levels and action buttons |
| **main.py** | Entry point — runs the poll → parse → notify → cleanup loop |

The service polls Gmail every 30 seconds (configurable), processes any new Jules emails it finds, and then removes them from your inbox.

## Setup

### Prerequisites

- Python 3.9+
- A Google Cloud project with the Gmail API enabled ([full guide](SETUP.md))
- The [ntfy app](https://play.google.com/store/apps/details?id=io.heckel.ntfy) installed on your phone

### Build

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### Configure

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` and set your ntfy topic:

```
NTFY_TOPIC=jules-notify-your-unique-name
```

Then subscribe to that same topic in the ntfy app on your phone.

Place your Google OAuth `credentials.json` in the project root. See [SETUP.md](SETUP.md) for step-by-step instructions.

### Run

```bash
# Verify notifications work
python main.py --test

# Check Gmail once and exit
python main.py --once

# Run continuously (Ctrl+C to stop)
python main.py
```

## Configuration

All settings live in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `NTFY_TOPIC` | *(required)* | Your ntfy channel name |
| `NTFY_SERVER` | `https://ntfy.sh` | ntfy server URL |
| `POLL_INTERVAL` | `30` | Seconds between Gmail checks |
| `EMAIL_ACTION` | `trash` | What to do after processing: `trash`, `archive`, or `read` |
| `GMAIL_QUERY` | `from:jules-notifications@google.com is:unread` | Gmail search filter |
