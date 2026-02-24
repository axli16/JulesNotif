"""
Jules Email Notification System
================================
Monitors Gmail for Google Jules notifications, sends push notifications
to your phone via ntfy, and cleans up processed emails.

Usage:
    python main.py                  # Run the monitoring loop
    python main.py --test           # Send a test notification
    python main.py --once           # Check once and exit (no loop)
"""

import os
import sys
import time
import signal
import argparse
from datetime import datetime

from dotenv import load_dotenv

from gmail_client import GmailClient
from email_parser import parse_jules_email
from notifier import Notifier


# ─── Configuration ──────────────────────────────────────────────

def load_config() -> dict:
    """Load configuration from .env file with sensible defaults."""
    load_dotenv()

    config = {
        "ntfy_topic": os.getenv("NTFY_TOPIC", ""),
        "ntfy_server": os.getenv("NTFY_SERVER", "https://ntfy.sh"),
        "poll_interval": int(os.getenv("POLL_INTERVAL", "30")),
        "email_action": os.getenv("EMAIL_ACTION", "trash"),
        "gmail_query": os.getenv("GMAIL_QUERY", "from:jules-notifications@google.com is:unread"),
    }

    # Validate required settings
    if not config["ntfy_topic"] or config["ntfy_topic"] == "jules-notify-CHANGE-ME":
        print("=" * 60)
        print("ERROR: NTFY_TOPIC is not configured!")
        print()
        print("1. Copy .env.example to .env")
        print("2. Set NTFY_TOPIC to a unique, hard-to-guess value")
        print("   Example: jules-notify-andrew-x7k2m")
        print("3. Subscribe to this topic in the ntfy app on your phone")
        print("=" * 60)
        sys.exit(1)

    return config


# ─── Main Loop ──────────────────────────────────────────────────

class JulesMonitor:
    """Main application class that ties everything together."""

    def __init__(self, config: dict):
        self.config = config
        self.gmail = GmailClient()
        self.notifier = Notifier(
            topic=config["ntfy_topic"],
            server=config["ntfy_server"],
        )
        self.running = True
        self.processed_count = 0

        # Set up graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n[Monitor] Shutting down... (processed {self.processed_count} emails this session)")
        self.running = False

    def start(self):
        """Authenticate and start the monitoring loop."""
        self._print_banner()
        self.gmail.authenticate()
        print(f"[Monitor] Monitoring Gmail with query: {self.config['gmail_query']}")
        print(f"[Monitor] Poll interval: {self.config['poll_interval']}s")
        print(f"[Monitor] Email cleanup action: {self.config['email_action']}")
        print(f"[Monitor] Notifications → ntfy topic: {self.config['ntfy_topic']}")
        print("-" * 60)

    def check_once(self) -> int:
        """
        Check Gmail once for Jules emails, process them, and return count.

        Returns:
            Number of emails processed.
        """
        now = datetime.now().strftime("%H:%M:%S")
        messages = self.gmail.get_jules_emails(self.config["gmail_query"])

        if not messages:
            print(f"[{now}] No new Jules emails.")
            return 0

        count = len(messages)
        print(f"[{now}] Found {count} Jules email(s)! Processing...")

        processed = 0
        for msg_meta in messages:
            msg_id = msg_meta["id"]

            # 1. Fetch full email content
            email_data = self.gmail.get_email_content(msg_id)
            if not email_data:
                print(f"  [!] Could not fetch email {msg_id}, skipping.")
                continue

            # 2. Parse Jules notification
            parsed = parse_jules_email(email_data)
            print(f"  → Status: {parsed['status']} | {parsed['title']}")

            # 3. Build notification message
            notif_message = self._build_notification_message(parsed)

            # 4. Send push notification
            sent = self.notifier.send_notification(
                title=parsed["title"],
                message=notif_message,
                status=parsed["status"],
                link=parsed.get("link", ""),
            )

            if not sent:
                print(f"  [!] Failed to send notification for {msg_id}, will retry next cycle.")
                continue

            # 5. Clean up email
            self.gmail.cleanup_email(msg_id, self.config["email_action"])
            processed += 1
            self.processed_count += 1

        print(f"[{now}] Processed {processed}/{count} emails.")
        return processed

    def run_loop(self):
        """Run the continuous monitoring loop."""
        self.start()

        while self.running:
            try:
                self.check_once()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[Monitor] Error during check: {e}")
                print("[Monitor] Will retry next cycle...")

            # Sleep in small increments so shutdown is responsive
            for _ in range(self.config["poll_interval"]):
                if not self.running:
                    break
                time.sleep(1)

        print("[Monitor] Goodbye!")

    def _build_notification_message(self, parsed: dict) -> str:
        """Build a human-readable notification message from parsed email data."""
        parts = []

        if parsed.get("repo"):
            parts.append(f"📦 Repo: {parsed['repo']}")

        if parsed.get("summary"):
            parts.append(parsed["summary"])

        if parsed.get("link"):
            parts.append(f"\n🔗 {parsed['link']}")

        return "\n".join(parts) if parts else "New update from Jules"

    def _print_banner(self):
        """Print the startup banner."""
        print()
        print("╔══════════════════════════════════════════════╗")
        print("║    🚀 Jules Email Notification Monitor       ║")
        print("║    Watching Gmail → Push to Phone            ║")
        print("╚══════════════════════════════════════════════╝")
        print()


# ─── CLI Entry Point ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Monitor Gmail for Jules notifications and push them to your phone."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test notification to verify ntfy is working.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check Gmail once and exit (no continuous loop).",
    )

    args = parser.parse_args()
    config = load_config()

    if args.test:
        print("Sending test notification...")
        notifier = Notifier(topic=config["ntfy_topic"], server=config["ntfy_server"])
        success = notifier.send_test()
        if success:
            print("✅ Test notification sent! Check your phone.")
        else:
            print("❌ Failed to send test notification. Check your ntfy settings.")
        sys.exit(0 if success else 1)

    monitor = JulesMonitor(config)

    if args.once:
        monitor.start()
        count = monitor.check_once()
        print(f"Done. Processed {count} email(s).")
        sys.exit(0)

    # Default: run the continuous monitoring loop
    monitor.run_loop()


if __name__ == "__main__":
    main()
