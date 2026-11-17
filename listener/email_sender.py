"""Sends the reply email: editorial HTML plus a plain-text alternative, links only."""

import os
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "0") == "1"
FROM_ADDR = os.environ.get("FROM_ADDR", "arxiv-digest@local")
REPLY_TO = os.environ.get("REPLY_TO", "").strip()
SUBSCRIPTIONS_DOMAIN = os.environ.get("SUBSCRIPTIONS_DOMAIN", "localhost").strip()
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Module-level Jinja env, reused across sends
_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def _pretty_numbers(nums: list[int]) -> str:
    """Format [1] -> 'paper 1'; [1,3] -> 'papers 1 and 3'; [1,2,3] -> 'papers 1, 2, and 3'."""
    if not nums:
        return ""
    if len(nums) == 1:
        return f"paper {nums[0]}"
    if len(nums) == 2:
        return f"papers {nums[0]} and {nums[1]}"
    return "papers " + ", ".join(str(n) for n in nums[:-1]) + f", and {nums[-1]}"


def _extract_issue_num(subject: str) -> str | None:
    """Extract '7' from the subject 'The Daily Abstract No. 7 - ...'."""
    m = re.search(r"No\.\s*(\d+)", subject)
    return m.group(1) if m else None


def send_reply(
    to_addr: str,
    original_subject: str,
    papers: list[dict[str, Any]],
    manage_url: str | None = None,
    unsubscribe_url: str | None = None,
) -> None:
    """Compose and send the reply listing each paper with its arXiv abs and PDF links.

    `papers` items carry `number`, `title` and `arxiv_id`; only their numbers
    are quoted, so out-of-range requests never appear. Nothing is attached:
    papers are linked until per-paper licenses are stored. SMTP errors propagate.
    """
    # The inbound subject is untrusted: a decoded CR/LF would make EmailMessage
    # reject the header (or, elsewhere, inject one), so fold it onto one line.
    subject_clean = " ".join(original_subject.split())
    subject_clean = subject_clean.replace("Re: ", "").replace("RE: ", "")
    noun = "paper" if len(papers) == 1 else "papers"
    subject = f"Re: {subject_clean} — {len(papers)} {noun}"

    context = {
        "numbers_pretty": _pretty_numbers([p["number"] for p in papers]),
        "papers": papers,
        "issue_num": _extract_issue_num(original_subject),
        "manage_url": manage_url,
        "unsubscribe_url": unsubscribe_url,
    }
    text_body = _env.get_template("reply.txt").render(**context)
    html_body = _env.get_template("reply.html").render(**context)

    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = to_addr
    if REPLY_TO:
        msg["Reply-To"] = REPLY_TO
    msg["Subject"] = subject
    if unsubscribe_url:
        msg["List-Id"] = f"The Daily Abstract <digest.{SUBSCRIPTIONS_DOMAIN}>"
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        if SMTP_USE_TLS:
            s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
