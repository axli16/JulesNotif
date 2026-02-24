# Jules Email Notification System — Setup Guide

## Prerequisites
- Python 3.9+
- A Google account with Gmail
- An Android phone (Samsung Galaxy S22+ or any Android device)

---

## Step 1: Google Cloud — Gmail API Setup

1. Go to **[Google Cloud Console](https://console.cloud.google.com/)**
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**
4. Search for **"Gmail API"** and click **Enable**
5. Go to **APIs & Services → Credentials**
6. Click **+ CREATE CREDENTIALS → OAuth client ID**
   - If prompted, configure the **OAuth Consent Screen** first:
     - Choose **External** user type
     - Fill in app name (e.g., "Jules Notifier"), your email
     - Add scope: `https://mail.google.com/`
     - Add your email as a **Test user**
     - Save
7. Create OAuth client:
   - Application type: **Desktop app**
   - Name: "Jules Notifier"
   - Click **Create**
8. Click **⬇ Download JSON** on the created credential
9. **Rename the file** to `credentials.json` and place it in the project root (`f:\JulesNotif\`)

> **Note:** Since the app is in "Testing" mode, only your test users can authenticate. This is fine for personal use.

---

## Step 2: Phone — Install ntfy App

1. Open the **Google Play Store** on your Samsung Galaxy S22+
2. Search for **"ntfy"** and install it (by Philipp C. Heckel)
3. Open the app and tap **+ Subscribe**
4. Enter your chosen topic name (e.g., `jules-notify-andrew-x7k2m`)
   - ⚠️ **Use a unique, hard-to-guess name** — anyone who knows the topic can send messages to it
5. Tap **Subscribe**
6. *(Optional)* In the ntfy app settings, you can customize notification sounds and display

---

## Step 3: Project Setup

Open a terminal in the project directory:

```bash
# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create your config file
copy .env.example .env
```

Edit `.env` and set your ntfy topic:
```
NTFY_TOPIC=jules-notify-andrew-x7k2m
```

---

## Step 4: First Run

```bash
# Test that ntfy notifications work
python main.py --test

# If you see ✅, check your phone — you should have a notification!
# If it fails, double-check your NTFY_TOPIC matches your phone subscription.

# Authenticate with Gmail (opens a browser window)
python main.py --once

# Follow the Google sign-in flow in your browser.
# After signing in, the app will check for Jules emails once and exit.
```

---

## Step 5: Run Continuously

```bash
python main.py
```

The service will check Gmail every 30 seconds (configurable in `.env`).

Press `Ctrl+C` to stop.

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `NTFY_TOPIC` | *(required)* | Your ntfy channel topic name |
| `NTFY_SERVER` | `https://ntfy.sh` | ntfy server URL |
| `POLL_INTERVAL` | `30` | Seconds between Gmail checks |
| `EMAIL_ACTION` | `trash` | Action after processing: `trash`, `archive`, `read` |
| `GMAIL_QUERY` | `from:jules-notifications@google.com is:unread` | Gmail search filter |

---

## Running as a Background Service (Optional)

### Option A: Windows Task Scheduler
1. Open **Task Scheduler**
2. Create a Basic Task → name it "Jules Notifier"
3. Trigger: **At logon**
4. Action: **Start a program**
   - Program: `f:\JulesNotif\venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `f:\JulesNotif`
5. Check "Run whether user is logged in or not" in properties

### Option B: Run in a terminal
Simply keep a terminal open with `python main.py` running.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `credentials.json not found` | Download OAuth credentials from Google Cloud Console (Step 1) |
| `NTFY_TOPIC is not configured` | Copy `.env.example` to `.env` and set your topic name |
| No notification on phone | Verify you subscribed to the same topic in the ntfy app |
| Gmail auth fails | Delete `token.json` and re-run to re-authenticate |
| `403 Forbidden` from Gmail | Ensure Gmail API is enabled and your email is in test users |
