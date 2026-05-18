"""Envia el reply con PDFs adjuntos."""

import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

logger = logging.getLogger("listener")

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
FROM_ADDR = "arxiv-digest@local"
TO_ADDR = os.environ.get("RECIPIENT", "fer@local")


def send_reply(
    original_subject: str, numbers: list[int], pdfs: list[dict[str, Any]]
) -> None:
    """Compone email con los PDFs como attachments y los limpia al final."""
    subject_clean = original_subject.replace("Re: ", "").replace("RE: ", "")
    subject = f"Re: {subject_clean} - {len(pdfs)} PDFs"
    body_lines = [f"PDFs solicitados: {numbers}", "", "Aqui los adjuntos:", ""]
    for p in pdfs:
        body_lines.append(f"  [{p['number']:>2}] {p['title']}")
    body_lines.append("")
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = TO_ADDR
    msg["Subject"] = subject
    msg.set_content("\n".join(body_lines))
    for p in pdfs:
        path = Path(p["path"])
        msg.add_attachment(
            path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=path.name,
        )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)
    logger.info("RESULT: reply enviado con %d PDFs", len(pdfs))
    for p in pdfs:
        Path(p["path"]).unlink(missing_ok=True)
