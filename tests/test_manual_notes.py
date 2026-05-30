"""Test per il supporto note manuali in `MeetWiki/manual/`.

Verifica:
- validate_manual_note_frontmatter accetta schema rilassato
- collect_actions estrae action items da note manuali con flag is_manual
- build_index BM25 include le note manuali
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import meetwiki_actions as actions  # noqa: E402
import meetwiki_ask as ask  # noqa: E402
import meetwiki_common as common  # noqa: E402


# ---- validate_manual_note_frontmatter ----

def test_manual_fm_minimal_ok():
    fm = {"id": "2026-06-03-x", "title": "T", "date": "2026-06-03"}
    assert common.validate_manual_note_frontmatter(fm) == []


def test_manual_fm_missing_required():
    fm = {"id": "x"}  # title + date mancanti
    errs = common.validate_manual_note_frontmatter(fm)
    assert any("title" in e for e in errs)
    assert any("date" in e for e in errs)


def test_manual_fm_bad_date():
    fm = {"id": "x", "title": "T", "date": "not-a-date"}
    errs = common.validate_manual_note_frontmatter(fm)
    assert any("date non valida" in e for e in errs)


def test_manual_fm_no_source_required():
    """Schema rilassato: NON richiede source/source_hash/ingested_at."""
    fm = {"id": "x", "title": "T", "date": "2026-06-03"}
    assert common.validate_manual_note_frontmatter(fm) == []
    # invece validate_note_frontmatter standard li richiederebbe
    errs = common.validate_note_frontmatter(fm)
    assert any("source" in e for e in errs)


# ---- collect_actions con note manuali ----

def test_collect_actions_includes_manual(tmp_path, monkeypatch):
    """Crea wiki temporanea con una nota canonica + una manuale, verifica scan."""
    wiki = tmp_path / "MeetWiki"
    (wiki / "notes" / "2026-06").mkdir(parents=True)
    (wiki / "manual" / "prep").mkdir(parents=True)
    (wiki / ".meta").mkdir(parents=True)

    # nota canonica
    (wiki / "notes" / "2026-06" / "2026-06-01-meet.md").write_text(
        '---\nid: 2026-06-01-meet\ntitle: "Meet"\ndate: 2026-06-01\n'
        'source: "x.md"\nsource_hash: "sha256:abc"\ningested_at: 2026-06-01T10:00:00\n'
        'participants: []\ntags: []\nrelated_docs: []\n---\n\n'
        "## Action Items\n\n- [ ] [Alice] Task canonico\n",
        encoding="utf-8",
    )
    # nota manuale
    (wiki / "manual" / "prep" / "2026-06-03-prep.md").write_text(
        '---\nid: 2026-06-03-prep\ntitle: "Prep"\ndate: 2026-06-03\n---\n\n'
        "## Action Items\n\n- [ ] [Bob] Task manuale\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(actions, "WIKI", wiki)
    monkeypatch.setattr(actions, "NOTES", wiki / "notes")
    monkeypatch.setattr(actions, "MANUAL", wiki / "manual")
    monkeypatch.setattr(actions, "STATUS_FILE", wiki / ".meta" / "actions_status.json")

    items = actions.collect_actions()
    assert len(items) == 2
    by_owner = {i["owner"]: i for i in items}
    assert by_owner["Alice"]["is_manual"] is False
    assert by_owner["Bob"]["is_manual"] is True
    assert by_owner["Bob"]["note_path"].startswith("manual/")


# ---- build_index con note manuali ----

def test_build_index_includes_manual(tmp_path, monkeypatch):
    wiki = tmp_path / "MeetWiki"
    (wiki / "notes" / "2026-06").mkdir(parents=True)
    (wiki / "manual").mkdir(parents=True)
    (wiki / ".meta").mkdir(parents=True)

    (wiki / "notes" / "2026-06" / "2026-06-01-meet.md").write_text(
        '---\nid: 2026-06-01-meet\ntitle: "Meet canonico"\ndate: 2026-06-01\n'
        'source: "x.md"\nsource_hash: "sha256:abc"\ningested_at: 2026-06-01T10:00:00\n'
        'participants: []\ntags: []\nrelated_docs: []\n---\n\n'
        "## Riepilogo\nContenuto canonico ricercabile.\n",
        encoding="utf-8",
    )
    (wiki / "manual" / "todo.md").write_text(
        '---\nid: 2026-06-03-todo\ntitle: "Todo manuale"\ndate: 2026-06-03\n---\n\n'
        "## Riepilogo\nContenuto manuale ricercabile unico.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(ask, "WIKI", wiki)
    monkeypatch.setattr(ask, "NOTES", wiki / "notes")
    monkeypatch.setattr(ask, "MANUAL", wiki / "manual")

    idx = ask.build_index()
    manual_chunks = [d for d in idx["docs"] if d.get("is_manual")]
    canonical_chunks = [d for d in idx["docs"] if not d.get("is_manual")]
    assert len(manual_chunks) > 0
    assert len(canonical_chunks) > 0
    # path della nota manuale parte da manual/
    assert all(d["path"].startswith("manual/") for d in manual_chunks)
