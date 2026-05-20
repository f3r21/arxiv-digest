"""Logica de seleccion de papers per-suscriptor (main._papers_for_subscriber)."""

import pytest

import main
from subscriber_repo import Subscriber


PAPERS = [
    {
        "arxiv_id": "p-dc",
        "title": "Kubernetes Distributed Foo",
        "abstract": "Pods on clusters.",
        "authors": ["A"],
        "categories": ["cs.DC"],
    },
    {
        "arxiv_id": "p-ai",
        "title": "Transformer Networks",
        "abstract": "Attention everywhere.",
        "authors": ["B"],
        "categories": ["cs.LG", "cs.AI"],
    },
    {
        "arxiv_id": "p-ai-rl",
        "title": "Reinforcement Learning",
        "abstract": "Sparse rewards in Atari games.",
        "authors": ["C"],
        "categories": ["cs.AI"],
    },
]


@pytest.fixture
def isolate_repo(monkeypatch):
    """Mock get_unseen_for: todos los papers son 'nuevos' para este test."""
    monkeypatch.setattr(
        main, "get_unseen_for",
        lambda sub_id, ids: set(ids),
    )


def test_subscriber_with_only_cs_dc(isolate_repo):
    sub = Subscriber(id=1, email="a@x", categories=["cs.DC"], keywords=[], max_papers=10)
    picked = main._papers_for_subscriber(sub, PAPERS)
    assert [p["arxiv_id"] for p in picked] == ["p-dc"]


def test_subscriber_keyword_filter(isolate_repo):
    sub = Subscriber(
        id=1, email="a@x", categories=["cs.AI", "cs.LG"],
        keywords=["transformer"], max_papers=10,
    )
    picked = main._papers_for_subscriber(sub, PAPERS)
    assert [p["arxiv_id"] for p in picked] == ["p-ai"]


def test_subscriber_no_keywords_passes_all_in_category(isolate_repo):
    sub = Subscriber(id=1, email="a@x", categories=["cs.AI"], keywords=[], max_papers=10)
    picked = main._papers_for_subscriber(sub, PAPERS)
    assert {p["arxiv_id"] for p in picked} == {"p-ai", "p-ai-rl"}


def test_subscriber_max_papers_caps(isolate_repo):
    sub = Subscriber(id=1, email="a@x", categories=["cs.AI"], keywords=[], max_papers=1)
    picked = main._papers_for_subscriber(sub, PAPERS)
    assert len(picked) == 1


def test_subscriber_with_no_matching_category(isolate_repo):
    sub = Subscriber(id=1, email="a@x", categories=["math.AG"], keywords=[], max_papers=10)
    picked = main._papers_for_subscriber(sub, PAPERS)
    assert picked == []


def test_already_seen_excluded(monkeypatch):
    """Si get_unseen_for devuelve set() vacio, no debe pickear nada."""
    monkeypatch.setattr(main, "get_unseen_for", lambda sub_id, ids: set())
    sub = Subscriber(id=1, email="a@x", categories=["cs.DC"], keywords=[], max_papers=10)
    picked = main._papers_for_subscriber(sub, PAPERS)
    assert picked == []
