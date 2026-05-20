"""download_pdfs ahora toma snapshot explicito (no lee disco global)."""

from unittest.mock import MagicMock, patch

from pdf_downloader import _slugify, download_pdfs


def test_slugify_drops_special_chars():
    assert _slugify("Hello, World! Foo*Bar") == "Hello_World_Foo_Bar"


def test_slugify_truncates():
    assert len(_slugify("a" * 100, max_len=20)) == 20


def test_download_pdfs_skips_out_of_range():
    papers = [{"arxiv_id": "1", "title": "A", "authors": ["X Y"],
               "published": "2026-01-01", "pdf_url": "http://x"}]
    # numero 5 cuando solo hay 1 paper → skip
    result = download_pdfs([5], papers)
    assert result == []


def test_download_pdfs_empty_input():
    assert download_pdfs([], []) == []


@patch("pdf_downloader.requests.get")
def test_download_pdfs_happy_path(mock_get, tmp_path, monkeypatch):
    import pdf_downloader
    monkeypatch.setattr(pdf_downloader, "PDFS_DIR", tmp_path)
    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    fake_resp.iter_content = MagicMock(return_value=[b"%PDF-1.4 fake content"])
    mock_get.return_value.__enter__ = lambda *_: fake_resp
    mock_get.return_value = fake_resp
    papers = [{
        "arxiv_id": "1706.03762",
        "title": "Attention Is All You Need",
        "authors": ["Vaswani et al."],
        "published": "2017-06-12",
        "pdf_url": "http://arxiv.org/pdf/1706.03762",
    }]
    result = download_pdfs([1], papers)
    assert len(result) == 1
    assert result[0]["number"] == 1
    assert result[0]["arxiv_id"] == "1706.03762"
    assert result[0]["path"].endswith(".pdf")
