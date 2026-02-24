"""
Push notification sender using ntfy.sh.
Sends Jules task notifications to your phone with appropriate priority, emoji, and actions.
"""

import requests


# Map Jules task statuses to ntfy priority levels and emoji tags
STATUS_CONFIG = {
    "completed": {
        "priority": "default",
        "tags": ["white_check_mark", "jules"],
        "emoji": "✅",
    },
    "failed": {
        "priority": "high",
        "tags": ["x", "jules", "warning"],
        "emoji": "❌",
    },
    "needs_review": {
        "priority": "high",
        "tags": ["eyes", "jules"],
        "emoji": "👀",
    },
    "in_progress": {
        "priority": "low",
        "tags": ["hourglass", "jules"],
        "emoji": "⏳",
    },
    "cancelled": {
        "priority": "default",
        "tags": ["no_entry_sign", "jules"],
        "emoji": "🚫",
    },
    "unknown": {
        "priority": "default",
        "tags": ["bell", "jules"],
        "emoji": "🔔",
    },
}


class Notifier:
    """Sends push notifications to phone via ntfy."""

    def __init__(self, topic: str, server: str = "https://ntfy.sh"):
        """
        Initialize the notifier.

        Args:
            topic: The ntfy topic to publish to (acts as a channel ID).
            server: The ntfy server URL (default: https://ntfy.sh).
        """
        self.topic = topic
        self.server = server.rstrip("/")
        self.url = f"{self.server}/{self.topic}"

    def send_notification(
        self,
        title: str,
        message: str,
        status: str = "unknown",
        link: str = "",
    ) -> bool:
        """
        Send a push notification to the phone.

        Args:
            title: Notification title
            message: Notification body
            status: Jules task status (completed, failed, needs_review, etc.)
            link: Optional URL to open when notification is clicked

        Returns:
            True if sent successfully, False otherwise
        """
        config = STATUS_CONFIG.get(status, STATUS_CONFIG["unknown"])

        # HTTP headers are latin-1 encoded, so strip any characters
        # that can't be represented. Emoji and unicode go in the body instead.
        safe_title = self._make_header_safe(f"Jules: {title}")

        # Prepend emoji to the message body where UTF-8 is supported
        full_message = f"{config['emoji']} {message}"

        headers = {
            "Title": safe_title,
            "Priority": config["priority"],
            "Tags": ",".join(config["tags"]),
        }

        # Add click action if we have a link
        if link:
            headers["Click"] = link
            headers["Actions"] = f"view, Open in Browser, {link}"

        try:
            response = requests.post(
                self.url,
                data=full_message.encode("utf-8"),
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                print(f"[Notify] Notification sent: {safe_title}")
                return True
            else:
                print(f"[Notify] Failed to send notification: HTTP {response.status_code}")
                print(f"[Notify] Response: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print("[Notify] Notification send timed out.")
            return False
        except requests.exceptions.ConnectionError:
            print(f"[Notify] Could not connect to ntfy server at {self.server}")
            return False
        except Exception as e:
            print(f"[Notify] Unexpected error sending notification: {e}")
            return False

    @staticmethod
    def _make_header_safe(text: str) -> str:
        """Strip characters that can't be encoded in latin-1 (HTTP header encoding)."""
        return text.encode("latin-1", errors="ignore").decode("latin-1")

    def send_test(self) -> bool:
        """Send a test notification to verify the setup works."""
        return self.send_notification(
            title="Connection Test",
            message="Jules Notifier is connected and working!\nYou will receive notifications here when Jules updates arrive.",
            status="completed",
        )
