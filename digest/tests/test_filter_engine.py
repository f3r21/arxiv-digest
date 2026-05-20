"""filter_engine: pura, sin estado, se llama N veces per-subscriber."""

from filter_engine import apply_filters


PAPER_KUBE = {
    "arxiv_id": "1",
    "title": "Kubernetes Scheduling",
    "abstract": "Optimizing pod placement on Kubernetes clusters.",
    "authors": ["Alice Doe"],
    "categories": ["cs.DC"],
}
PAPER_TRANS = {
    "arxiv_id": "2",
    "title": "Linear Transformers",
    "abstract": "A transformer architecture with linear attention.",
    "authors": ["Bob Smith"],
    "categories": ["cs.LG"],
}
PAPER_RL = {
    "arxiv_id": "3",
    "title": "Sparse Reward RL",
    "abstract": "Reinforcement learning from sparse signals.",
    "authors": ["Carol Wu"],
    "categories": ["cs.AI"],
}


def test_keyword_match_in_title():
    out = apply_filters(
        [PAPER_KUBE, PAPER_TRANS], {"keywords": ["transformer"], "authors": []}
    )
    assert len(out) == 1
    assert out[0]["arxiv_id"] == "2"
    assert "transformer" in out[0]["match_reason"]


def test_keyword_match_in_abstract():
    out = apply_filters(
        [PAPER_KUBE], {"keywords": ["pod"], "authors": []}
    )
    assert len(out) == 1


def test_author_match():
    out = apply_filters(
        [PAPER_KUBE, PAPER_TRANS], {"keywords": [], "authors": ["Smith"]}
    )
    assert len(out) == 1
    assert out[0]["arxiv_id"] == "2"
    assert "autor:Smith" in out[0]["match_reason"]


def test_empty_filters_returns_nothing():
    out = apply_filters([PAPER_KUBE, PAPER_TRANS], {"keywords": [], "authors": []})
    assert out == []


def test_case_insensitive_keywords():
    out = apply_filters(
        [PAPER_TRANS], {"keywords": ["TRANSFORMER"], "authors": []}
    )
    assert len(out) == 1


def test_multiple_keywords_or_logic():
    out = apply_filters(
        [PAPER_KUBE, PAPER_TRANS, PAPER_RL],
        {"keywords": ["kubernetes", "reinforcement"], "authors": []},
    )
    assert {p["arxiv_id"] for p in out} == {"1", "3"}
