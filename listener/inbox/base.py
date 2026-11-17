"""Common contract for inbox backends.

Listing and body fetch are separate calls so the listener can skip messages it
already processed before paying for their body (Mailsac bills every API call).

`list_messages` returns one dict per message with the keys:
    id        str  - unique message id
    subject   str  - subject line
    sender    str  - sender email
    recipient str  - recipient email (the inbox itself)
"""

from typing import Protocol


class InboxBackend(Protocol):
    """Structural protocol: any object with these methods qualifies."""

    def list_messages(self) -> list[dict]:
        """Return message metadata (no body). Raises on network or HTTP errors."""
        ...

    def fetch_body(self, msg_id: str) -> str:
        """Return the plain-text body of one message. Raises on network or HTTP errors."""
        ...

    def delete_message(self, msg_id: str) -> None:
        """Best effort: remove the message from the backend. Never raises."""
        ...
