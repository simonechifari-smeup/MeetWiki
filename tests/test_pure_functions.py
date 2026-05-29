"""Test suite minimale per le funzioni pure di MeetWiki.

Esegui con: `.\\.venv\\Scripts\\python.exe -m pytest -q`
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import meetwiki_actions as actions  # noqa: E402
import meetwiki_ask as ask  # noqa: E402
import meetwiki_common as common  # noqa: E402
import meetwiki_digest as digest  # noqa: E402
import meetwiki_ingest as ingest  # noqa: E402

# ---- meetwiki_common ----

def test_slugify_basic():
    assert common.slugify("Hello World") == "hello-world"
    assert common.slugify("Caffè Latté") == "caffe-latte"


def test_slugify_maxlen_and_fallback():
    assert common.slugify("abcdefghij", maxlen=4) == "abcd"
    assert common.slugify("!!!", fallback="anon") == "anon"


def test_parse_frontmatter_basic():
    text = '---\ntitle: "Foo"\ndate: 2026-05-29\ntags:\n  - a\n  - b\n---\nbody here'
    fm, body = common.parse_frontmatter(text)
    assert fm == {"title": "Foo", "date": "2026-05-29", "tags": ["a", "b"]}
    assert body.strip() == "body here"


def test_parse_frontmatter_missing():
    fm, body = common.parse_frontmatter("no frontmatter here")
    assert fm == {}
    assert body == "no frontmatter here"


def test_extract_section_levels():
    body = "## Riepilogo\nciao\n## Action Items\n- [ ] task\n"
    assert common.extract_section(body, "Riepilogo") == "ciao"
    body3 = "### Tema\nX\n### Altro\nY\n"
    assert common.extract_section(body3, "Tema", level=3) == "X"


def test_atomic_write_and_safe_load_roundtrip(tmp_path):
    p = tmp_path / "x.json"
    common.atomic_write_json(p, {"a": 1, "b": [2, 3]})
    assert common.safe_load_json(p, {}) == {"a": 1, "b": [2, 3]}


def test_safe_load_json_corrupt(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{not json", encoding="utf-8")
    out = common.safe_load_json(p, default={"fallback": True})
    assert out == {"fallback": True}
    backups = list(tmp_path.glob("x.json.corrupt.*"))
    assert len(backups) == 1


# ---- meetwiki_ingest ----

def test_kw_match_word_boundary():
    assert ingest._kw_match("team", "team acronis")
    assert ingest._kw_match("team", "team_acronis")
    assert ingest._kw_match("team", "team-acronis")
    assert not ingest._kw_match("team", "teamacronis")


def test_parse_filename_timestamp():
    d, t, lang = ingest.parse_filename(
        "2026-05-20 - Daily DC - 2026_05_20 10_00 CEST - Appunti di Gemini (Italian).md"
    )
    assert d == "2026-05-20"
    assert "Daily DC" in t
    assert lang == "italian"


def test_parse_filename_no_date_returns_none():
    d, _, _ = ingest.parse_filename("random.md")
    assert d is None


def test_select_canonical_prefers_italian():
    files = [
        Path("2026-05-29 - Foo - 2026_05_27 10_00 CEST - Notes by Gemini (English).md"),
        Path("2026-05-29 - Foo - 2026_05_27 10_00 CEST - Notes by Gemini (Italian).md"),
    ]
    canonical, dup_map = ingest.select_canonical(files)
    assert len(canonical) == 1
    assert "(Italian)" in canonical[0].name
    assert len(dup_map) == 1


# ---- meetwiki_actions ----

def test_split_owners():
    assert actions.split_owners("Andrea, Filippo") == ["Andrea", "Filippo"]
    assert actions.split_owners("Andrea e Filippo") == ["Andrea", "Filippo"]
    assert actions.split_owners("Il gruppo") == ["Il gruppo"]
    assert actions.split_owners("") == ["Non assegnato"]


def test_action_hash_stable():
    a = actions.action_hash("Mario", "Fare X", "note-1")
    b = actions.action_hash("Mario", "Fare X", "note-1")
    c = actions.action_hash("Mario", "Fare Y", "note-1")
    assert a == b
    assert a != c
    assert len(a) == 10


def test_actions_slugify_fallback():
    assert actions.slugify("!!!") == "anonimo"


# ---- meetwiki_ask ----

def test_tokenize_strips_stopwords_and_accents():
    toks = ask.tokenize("Il meet è andato bene con Acronis")
    assert "acronis" in toks
    assert "meet" in toks
    assert "il" not in toks
    assert "e" not in toks


# ---- meetwiki_digest ----

def test_week_range_wraps_year():
    # 2024-12-31 e' un martedi della settimana ISO 2025-W01
    monday, sunday, label = digest.week_range(date(2024, 12, 31))
    assert monday == date(2024, 12, 30)
    assert sunday == date(2025, 1, 5)
    assert label == "2025-W01"


def test_month_range_december():
    start, end, label = digest.month_range(date(2026, 12, 15))
    assert start == date(2026, 12, 1)
    assert end == date(2026, 12, 31)
    assert label == "2026-12"
