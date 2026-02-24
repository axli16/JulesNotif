"""
Parser for Google Jules notification emails.
Extracts task status, repository, summary, and links from email content.
"""

import re
from bs4 import BeautifulSoup


# Status keywords to look for in Jules emails
STATUS_PATTERNS = {
    "completed": [
        r"completed",
        r"finished",
        r"done",
        r"merged",
        r"task\s+complete",
        r"successfully",
    ],
    "failed": [
        r"failed",
        r"error",
        r"unable",
        r"could\s*n[o']t",
        r"unsuccessful",
    ],
    "needs_review": [
        r"review",
        r"waiting",
        r"pending",
        r"ready\s+for\s+review",
        r"pull\s+request",
        r"changes?\s+ready",
    ],
    "in_progress": [
        r"started",
        r"working",
        r"in\s+progress",
        r"processing",
        r"running",
    ],
    "cancelled": [
        r"cancell?ed",
        r"stopped",
        r"aborted",
    ],
}


def parse_jules_email(email_data: dict) -> dict:
    """
    Parse a Jules notification email and extract structured information.

    Args:
        email_data: Dict from GmailClient.get_email_content() with keys:
            subject, snippet, body_html, body_text

    Returns:
        Dict with keys:
            - status: One of 'completed', 'failed', 'needs_review', 'in_progress', 'cancelled', 'unknown'
            - title: The notification title (cleaned subject line)
            - repo: Repository name if found
            - summary: Human-readable summary of the notification
            - link: Link to the Jules task if found
            - raw_subject: Original subject line
    """
    subject = email_data.get("subject", "")
    snippet = email_data.get("snippet", "")
    body_html = email_data.get("body_html", "")
    body_text = email_data.get("body_text", "")

    # Parse HTML body for cleaner text extraction
    body_plain = body_text
    if body_html:
        body_plain = _html_to_text(body_html)

    # Combine all text for analysis
    full_text = f"{subject} {snippet} {body_plain}".lower()

    result = {
        "status": _detect_status(full_text),
        "title": _clean_subject(subject),
        "repo": _extract_repo(full_text, subject),
        "summary": _build_summary(snippet, body_plain),
        "link": _extract_jules_link(body_html, body_plain),
        "raw_subject": subject,
    }

    return result


def _html_to_text(html: str) -> str:
    """Convert HTML email body to plain text."""
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for tag in soup(["script", "style", "head"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Collapse multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception:
        return html


def _detect_status(text: str) -> str:
    """
    Detect the Jules task status from email text.
    Returns the most likely status based on keyword matching.
    """
    scores = {}

    for status, patterns in STATUS_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            score += len(matches)
        if score > 0:
            scores[status] = score

    if not scores:
        return "unknown"

    # Return the status with the highest score
    return max(scores, key=scores.get)


def _clean_subject(subject: str) -> str:
    """Clean up the email subject line for use as a notification title."""
    # Remove common prefixes
    subject = re.sub(r"^\s*\[Jules\]\s*", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"^\s*Jules:\s*", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"^\s*Google Jules\s*[-–—:]\s*", "", subject, flags=re.IGNORECASE)

    return subject.strip() or "Jules Notification"


def _extract_repo(text: str, subject: str) -> str:
    """Try to extract a repository name from the email."""
    # Look for GitHub-style repo references (owner/repo)
    repo_patterns = [
        r"(?:repository|repo)[:\s]+([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)",
        r"github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)",
        r"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)(?:\s+repository)",
    ]

    for pattern in repo_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    # Check subject for repo-like pattern
    match = re.search(r"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)", subject)
    if match:
        candidate = match.group(1)
        # Filter out obvious non-repo matches
        if "/" in candidate and not candidate.startswith("http"):
            return candidate

    return ""


def _build_summary(snippet: str, body_text: str) -> str:
    """Build a concise summary from the email content."""
    # Prefer the snippet (Gmail's auto-generated preview)
    if snippet:
        # Clean up HTML entities
        summary = snippet.replace("&#39;", "'").replace("&quot;", '"')
        summary = re.sub(r"&\w+;", "", summary)
        return summary[:300]  # Cap at 300 chars for notification

    # Fall back to first meaningful lines of body
    if body_text:
        lines = [line.strip() for line in body_text.split("\n") if line.strip()]
        # Take first 3 non-empty lines
        summary = " ".join(lines[:3])
        return summary[:300]

    return "New notification from Jules"


def _extract_jules_link(html: str, text: str) -> str:
    """Extract a link to the Jules task from the email."""
    # Try HTML first for accurate links
    if html:
        try:
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "jules" in href.lower() or "github.com" in href.lower():
                    return href
        except Exception:
            pass

    # Fall back to URL regex in plain text
    url_pattern = r"https?://[^\s<>\"')\]]+"
    urls = re.findall(url_pattern, text)
    for url in urls:
        if "jules" in url.lower() or "github.com" in url.lower():
            return url

    return ""
