"""End-to-end reply flow through poll_once with a fake inbox and a fake SMTP server."""

import db
import main
from tests.conftest import make_paper

PAPERS = [
    make_paper("2411.00001", "Attention Is Still All You Need"),
    make_paper("2411.00002", "Sparse Mixtures of Experts"),
    make_paper("2411.00003", "Diffusion for Tabular Data"),
]


def _bodies(msg) -> tuple[str, str]:
    text = msg.get_body(preferencelist=("plain",)).get_content()
    html = msg.get_body(preferencelist=("html",)).get_content()
    return text, html


def test_reply_lists_links_and_attaches_nothing(inbox, smtp, add_subscriber):
    add_subscriber("ana@example.com", PAPERS)
    inbox.add("m1", "ana@example.com", "1 3")

    main.poll_once(inbox)

    assert len(smtp.outbox) == 1
    sent = smtp.outbox[0]
    assert sent["To"] == "ana@example.com"
    assert list(sent.iter_attachments()) == []
    text, html = _bodies(sent)
    for body in (text, html):
        assert "Attention Is Still All You Need" in body
        assert "https://arxiv.org/abs/2411.00001" in body
        assert "https://arxiv.org/pdf/2411.00001" in body
        assert "Diffusion for Tabular Data" in body
        assert "https://arxiv.org/abs/2411.00003" in body
        assert "https://arxiv.org/pdf/2411.00003" in body
        assert "2411.00002" not in body
    assert "attached" not in text.lower()
    assert db.is_processed("m1")
    assert inbox.deleted == ["m1"]
