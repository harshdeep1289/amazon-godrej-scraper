#!/usr/bin/env python3
"""
Email utility to send the generated report via Gmail SMTP.

Configuration (via environment variables):
- EMAIL_SENDER: sender email (default: plansreport@gmail.com)
- EMAIL_APP_PASSWORD: Gmail App Password (required)
- EMAIL_RECIPIENTS: comma/newline/space separated list of recipients (required)

Optional fallback: create a file named `recipients.txt` with one email per line.
"""

import os
import smtplib
import mimetypes
from email.message import EmailMessage
from datetime import datetime
from typing import List, Optional


def _parse_recipients(raw: str) -> List[str]:
    if not raw:
        return []
    # Support comma, newline, or space separated
    parts = []
    for sep in [",", "\n", " "]:
        raw = raw.replace(sep, ";")
    for p in raw.split(";"):
        p = p.strip()
        if p:
            parts.append(p)
    # De-duplicate while preserving order
    seen = set()
    result = []
    for p in parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            result.append(p)
    return result


def load_recipients() -> List[str]:
    env_val = os.getenv("EMAIL_RECIPIENTS", "").strip()
    recips = _parse_recipients(env_val)
    if recips:
        return recips
    # Fallback to recipients.txt in project root
    try:
        if os.path.exists("recipients.txt"):
            with open("recipients.txt", "r", encoding="utf-8") as f:
                raw = f.read()
            return _parse_recipients(raw)
    except Exception:
        pass
    return []


def send_report(
    attachment_path: str,
    subject: Optional[str] = None,
    body: Optional[str] = None,
) -> bool:
    sender = os.getenv("EMAIL_SENDER", "plansreport@gmail.com").strip()
    app_password = os.getenv("EMAIL_APP_PASSWORD", "jmsy jvqy thgl hjcx").strip()
    recipients = load_recipients()

    if not sender or not app_password or not recipients:
        print(
            "⚠️ Skipping email: ensure EMAIL_APP_PASSWORD is set and EMAIL_RECIPIENTS has at least one address."
        )
        return False

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject or f"Godrej Report {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    msg.set_content(body or "Automated report attached.")

    # Attach file if present
    if attachment_path and os.path.exists(attachment_path):
        ctype, encoding = mimetypes.guess_type(attachment_path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(attachment_path, "rb") as fp:
            file_data = fp.read()
        msg.add_attachment(
            file_data,
            maintype=maintype,
            subtype=subtype,
            filename=os.path.basename(attachment_path),
        )
    else:
        print(f"⚠️ Attachment not found: {attachment_path}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.send_message(msg)
        print(f"✓ Email sent to {len(recipients)} recipient(s)")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False