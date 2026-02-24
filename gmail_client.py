"""
Gmail API client for monitoring and managing Jules notification emails.
"""

import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Full mailbox access needed to read, modify labels, and trash emails
SCOPES = ["https://mail.google.com/"]

# Path constants
TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")


class GmailClient:
    """Handles Gmail API authentication and email operations."""

    def __init__(self):
        self.service = None
        self.creds = None

    def authenticate(self):
        """
        Authenticate with Gmail API using OAuth2.
        On first run, opens a browser for Google sign-in.
        Subsequent runs use the saved token.
        """
        creds = None

        # Load existing token
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        # If no valid credentials, run the auth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("[Gmail] Refreshing expired token...")
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"credentials.json not found at {CREDENTIALS_PATH}.\n"
                        "Please download it from Google Cloud Console.\n"
                        "See SETUP.md for instructions."
                    )
                print("[Gmail] Starting OAuth2 flow — a browser window will open...")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for future runs
            with open(TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())
            print("[Gmail] Token saved successfully.")

        self.creds = creds
        self.service = build("gmail", "v1", credentials=creds)
        print("[Gmail] Authenticated successfully.")
        return self

    def get_jules_emails(self, query: str) -> list:
        """
        Search for Jules notification emails matching the given query.

        Args:
            query: Gmail search query string (e.g., 'from:jules-notifications@google.com is:unread')

        Returns:
            List of message metadata dicts with 'id' and 'threadId'.
        """
        try:
            results = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=20
            ).execute()

            messages = results.get("messages", [])
            return messages

        except Exception as e:
            print(f"[Gmail] Error searching emails: {e}")
            return []

    def get_email_content(self, msg_id: str) -> dict:
        """
        Fetch the full content of an email by its message ID.

        Returns:
            Dict with keys: id, subject, from, date, snippet, body_html, body_text
        """
        try:
            msg = self.service.users().messages().get(
                userId="me",
                id=msg_id,
                format="full"
            ).execute()

            headers = msg.get("payload", {}).get("headers", [])
            header_map = {h["name"].lower(): h["value"] for h in headers}

            email_data = {
                "id": msg["id"],
                "thread_id": msg.get("threadId", ""),
                "subject": header_map.get("subject", "(no subject)"),
                "from": header_map.get("from", ""),
                "date": header_map.get("date", ""),
                "snippet": msg.get("snippet", ""),
                "body_html": "",
                "body_text": "",
            }

            # Extract body from payload
            payload = msg.get("payload", {})
            email_data["body_html"], email_data["body_text"] = self._extract_body(payload)

            return email_data

        except Exception as e:
            print(f"[Gmail] Error fetching email {msg_id}: {e}")
            return {}

    def _extract_body(self, payload: dict) -> tuple:
        """
        Recursively extract HTML and plain text body from email payload.

        Returns:
            Tuple of (html_body, text_body)
        """
        html_body = ""
        text_body = ""

        mime_type = payload.get("mimeType", "")

        # Direct body data
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
            if "html" in mime_type:
                html_body = decoded
            elif "plain" in mime_type:
                text_body = decoded

        # Check parts recursively
        for part in payload.get("parts", []):
            part_html, part_text = self._extract_body(part)
            if part_html:
                html_body = part_html
            if part_text:
                text_body = part_text

        return html_body, text_body

    def trash_email(self, msg_id: str) -> bool:
        """Move an email to trash."""
        try:
            self.service.users().messages().trash(userId="me", id=msg_id).execute()
            print(f"[Gmail] Email {msg_id} moved to trash.")
            return True
        except Exception as e:
            print(f"[Gmail] Error trashing email {msg_id}: {e}")
            return False

    def archive_email(self, msg_id: str) -> bool:
        """Archive an email by removing the INBOX label."""
        try:
            self.service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"removeLabelIds": ["INBOX"]}
            ).execute()
            print(f"[Gmail] Email {msg_id} archived.")
            return True
        except Exception as e:
            print(f"[Gmail] Error archiving email {msg_id}: {e}")
            return False

    def mark_as_read(self, msg_id: str) -> bool:
        """Mark an email as read by removing the UNREAD label."""
        try:
            self.service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            print(f"[Gmail] Email {msg_id} marked as read.")
            return True
        except Exception as e:
            print(f"[Gmail] Error marking email {msg_id} as read: {e}")
            return False

    def cleanup_email(self, msg_id: str, action: str) -> bool:
        """
        Perform the configured cleanup action on an email.

        Args:
            msg_id: The Gmail message ID
            action: One of 'trash', 'archive', 'read'
        """
        action = action.lower().strip()
        if action == "trash":
            return self.trash_email(msg_id)
        elif action == "archive":
            return self.archive_email(msg_id)
        elif action == "read":
            return self.mark_as_read(msg_id)
        else:
            print(f"[Gmail] Unknown cleanup action: {action}. Defaulting to trash.")
            return self.trash_email(msg_id)
