"""Parseo de numeros en replies."""

from reply_parser import parse_reply


def test_simple_csv():
    assert parse_reply("quiero 1, 3 y 5") == [1, 3, 5]


def test_no_numbers():
    assert parse_reply("gracias por el digest") == []


def test_dedup_preserves_first_occurrence_order():
    assert parse_reply("quiero 3 luego 1 luego 3 de nuevo") == [3, 1]


def test_strips_gmail_quoted_text():
    body = """quiero el 2

On Mon, May 19, 2026 at 7:00 PM Someone wrote:
> 1   Paper viejo
> 2   Otro paper
> 5   tercer paper
"""
    assert parse_reply(body) == [2]


def test_strips_lines_starting_with_gt():
    body = """1, 4
> ignorame 9 9 9
> tambien 8
"""
    assert parse_reply(body) == [1, 4]


def test_caps_at_ten():
    body = " ".join(str(i) for i in range(1, 20))
    assert len(parse_reply(body)) == 10


def test_ignores_three_digit_numbers():
    assert parse_reply("quiero el 100 y el 5") == [5]


def test_zero_excluded():
    assert parse_reply("0 1 2") == [1, 2]
