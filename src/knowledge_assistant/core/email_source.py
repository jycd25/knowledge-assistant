"""Email as a knowledge source, over IMAP with only the standard library.

Works with any IMAP server; for Gmail use an app password. Messages are turned into
plain-text documents (headers + body) and deduplicated by Message-ID. Network access is
isolated behind the `Mailbox` protocol so the job handler is testable with a fake.
"""

from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass, field
from email.message import Message
from html.parser import HTMLParser
from typing import Protocol


@dataclass
class EmailDoc:
    uid: int
    message_id: str
    subject: str
    sender: str
    date: str
    text: str

    @property
    def title(self) -> str:
        return self.subject or "(no subject)"

    @property
    def content(self) -> str:
        return f"From: {self.sender}\nDate: {self.date}\nSubject: {self.subject}\n\n{self.text}"


class Mailbox(Protocol):
    def uids_after(self, folder: str, last_uid: int) -> list[int]: ...

    def fetch(self, folder: str, uid: int) -> bytes: ...


class ImapMailbox:
    def __init__(self, host: str, user: str, password: str, port: int = 993, ssl: bool = True):
        self._conn = (imaplib.IMAP4_SSL if ssl else imaplib.IMAP4)(host, port)
        self._conn.login(user, password)
        self._selected: str | None = None

    def _select(self, folder: str) -> None:
        if self._selected != folder:
            status, _ = self._conn.select(f'"{folder}"', readonly=True)
            if status != "OK":
                raise RuntimeError(f"cannot open IMAP folder {folder!r}")
            self._selected = folder

    def uids_after(self, folder: str, last_uid: int) -> list[int]:
        self._select(folder)
        status, data = self._conn.uid("search", None, f"UID {last_uid + 1}:*")
        if status != "OK":
            raise RuntimeError("IMAP search failed")
        return sorted(int(u) for u in data[0].split() if int(u) > last_uid)

    def fetch(self, folder: str, uid: int) -> bytes:
        self._select(folder)
        status, data = self._conn.uid("fetch", str(uid), "(BODY.PEEK[])")
        if status != "OK" or not data or not isinstance(data[0], tuple):
            raise RuntimeError(f"IMAP fetch failed for uid {uid}")
        return data[0][1]

    def close(self) -> None:
        try:
            self._conn.logout()
        except Exception:
            pass


# -- parsing -------------------------------------------------------------------------
class _HtmlText(HTMLParser):
    SKIP = {"script", "style", "head"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _HtmlText()
    p.feed(html)
    return re.sub(r"\n{3,}", "\n\n", "".join(p.parts)).strip()


def _body(msg: Message) -> str:
    plain, html = [], []
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            continue
        ctype = part.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        (plain if ctype == "text/plain" else html).append(text)
    if plain:
        return "\n".join(plain).strip()
    if html:
        return html_to_text("\n".join(html))
    return ""


def parse_email(uid: int, raw: bytes) -> EmailDoc:
    msg = email.message_from_bytes(raw)
    return EmailDoc(
        uid=uid,
        message_id=(msg.get("Message-ID") or f"<uid-{uid}>").strip(),
        subject=msg.get("Subject") or "",
        sender=msg.get("From") or "",
        date=msg.get("Date", ""),
        text=_body(msg),
    )


@dataclass
class FakeMailbox:
    """Test double: {folder: {uid: raw_bytes}}."""

    messages: dict[str, dict[int, bytes]] = field(default_factory=dict)

    def uids_after(self, folder: str, last_uid: int) -> list[int]:
        return sorted(u for u in self.messages.get(folder, {}) if u > last_uid)

    def fetch(self, folder: str, uid: int) -> bytes:
        return self.messages[folder][uid]
