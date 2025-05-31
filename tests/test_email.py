from email.message import EmailMessage

from knowledge_assistant.core.email_source import FakeMailbox, html_to_text, parse_email


def _raw(subject="Hi", body="plain body", html=None, mid="<m1@x>"):
    m = EmailMessage()
    m["From"] = "Ann <ann@example.com>"
    m["Subject"] = subject
    m["Message-ID"] = mid
    m["Date"] = "Mon, 2 Jun 2025 10:00:00 +0000"
    if html:
        m.set_content(body)
        m.add_alternative(html, subtype="html")
    else:
        m.set_content(body)
    return m.as_bytes()


def test_parse_plain_and_multipart_prefers_plain():
    d = parse_email(7, _raw(html="<p>ignored</p>"))
    assert d.uid == 7 and d.subject == "Hi" and d.message_id == "<m1@x>" and d.text == "plain body"
    assert d.content.startswith("From: Ann <ann@example.com>")


def test_html_only_is_converted_and_scripts_dropped():
    m = EmailMessage()
    m["Subject"] = "H"
    m.add_alternative("<html><head><style>x{}</style></head><body><p>One</p><script>bad()</script><p>Two &amp; three</p></body></html>", subtype="html")
    d = parse_email(1, m.as_bytes())
    assert d.text == "One\nTwo & three"
    assert html_to_text("<div>a</div><div>b</div>") == "a\nb"


def test_encoded_subject_and_missing_message_id():
    m = EmailMessage()
    m["Subject"] = "=?utf-8?b?w4TDtsO8?="  # "Äöü"
    m.set_content("x")
    d = parse_email(9, m.as_bytes())
    assert d.subject == "Äöü" and d.message_id == "<uid-9>"


def test_fake_mailbox_uids_after():
    mb = FakeMailbox({"INBOX": {3: b"", 5: b"", 9: b""}})
    assert mb.uids_after("INBOX", 4) == [5, 9] and mb.uids_after("INBOX", 9) == []
