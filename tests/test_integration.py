"""Integration test minimali (F34): ingest end-to-end, validate_note_frontmatter,
atomic_write_text. Usano `tmp_path` per non toccare il workspace reale."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import meetwiki_ingest as ingest  # noqa: E402
from meetwiki_common import atomic_write_text, validate_note_frontmatter  # noqa: E402


# ---------------------------------------------------------------------------
# validate_note_frontmatter
# ---------------------------------------------------------------------------
def _valid_fm() -> dict:
    return {
        "id": "2026-05-29-meeting-test",
        "title": "Meeting test",
        "date": "2026-05-29",
        "source": "note_riunioni/x.md",
        "source_hash": "sha256:abc",
        "ingested_at": "2026-05-29T10:00:00",
        "participants": ["Alice"],
        "tags": ["test"],
        "related_docs": [],
    }


def test_validate_note_frontmatter_accepts_valid():
    assert validate_note_frontmatter(_valid_fm()) == []


def test_validate_note_frontmatter_rejects_missing_id():
    fm = _valid_fm()
    fm.pop("id")
    errs = validate_note_frontmatter(fm)
    assert any("id" in e for e in errs)


def test_validate_note_frontmatter_rejects_bad_date():
    fm = _valid_fm()
    fm["date"] = "2026-13-01"
    errs = validate_note_frontmatter(fm)
    assert any("date" in e for e in errs)


def test_validate_note_frontmatter_rejects_non_list_tags():
    fm = _valid_fm()
    fm["tags"] = "not-a-list"
    errs = validate_note_frontmatter(fm)
    assert any("tags" in e for e in errs)


# ---------------------------------------------------------------------------
# atomic_write_text
# ---------------------------------------------------------------------------
def test_atomic_write_text_creates_and_replaces(tmp_path):
    out = tmp_path / "out.md"
    atomic_write_text(out, "v1")
    assert out.read_text(encoding="utf-8") == "v1"
    atomic_write_text(out, "v2")
    assert out.read_text(encoding="utf-8") == "v2"
    # No .tmp file leftover
    assert not (tmp_path / "out.md.tmp").exists()


def test_atomic_write_text_creates_parent_dirs(tmp_path):
    out = tmp_path / "deep" / "nested" / "file.md"
    atomic_write_text(out, "hello")
    assert out.read_text(encoding="utf-8") == "hello"


# ---------------------------------------------------------------------------
# Ingest end-to-end
# ---------------------------------------------------------------------------
SAMPLE_SOURCE = """# 2026-05-29 - Test meeting - 2026_05_29 10_00 CEST - Appunti di Gemini

### Riepilogo
Discussione di test per la pipeline di ingest.

### Dettagli
* **Argomento uno:** descrizione breve.
* **Argomento due:** altra descrizione.

### Passaggi successivi
- [ ] \\[Alice\\] preparare un follow-up entro venerdi'.
- [ ] \\[Bob\\] aggiornare il manifest.

[Alice](mailto:alice@example.com)
[Bob](mailto:bob@example.com)
"""


def test_ingest_creates_manifest_and_canonical_note(tmp_path, monkeypatch):
    """Smoke test end-to-end: scrive un sorgente, esegue ingest, verifica
    note canonica, manifest e archive."""
    source_dir = tmp_path / "note_riunioni"
    wiki_dir = tmp_path / "MeetWiki"
    notes_dir = wiki_dir / "notes"
    history_dir = notes_dir / "_history"
    manifest = wiki_dir / ".meta" / "manifest.json"

    monkeypatch.setattr(ingest, "SOURCE_DIR", source_dir)
    monkeypatch.setattr(ingest, "WIKI_DIR", wiki_dir)
    monkeypatch.setattr(ingest, "NOTES_DIR", notes_dir)
    monkeypatch.setattr(ingest, "HISTORY_DIR", history_dir)
    monkeypatch.setattr(ingest, "MANIFEST", manifest)

    source_dir.mkdir(parents=True)
    src_name = "2026-05-29 - Test meeting - 2026_05_29 10_00 CEST - Appunti di Gemini.md"
    (source_dir / src_name).write_text(SAMPLE_SOURCE, encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["meetwiki_ingest.py"])
    rc = ingest.main()
    assert rc == 0

    # Note canonical creata sotto notes/YYYY-MM/
    month_dir = notes_dir / "2026-05"
    assert month_dir.exists()
    notes = list(month_dir.glob("*.md"))
    assert len(notes) == 1
    note_content = notes[0].read_text(encoding="utf-8")
    assert "id: 2026-05-29-test-meeting" in note_content
    assert "date: 2026-05-29" in note_content

    # Manifest contiene la entry con generated_note_hash (F28)
    import json
    data = json.loads(manifest.read_text(encoding="utf-8"))
    ingested = data["ingested"]
    # La entry e' sotto il nome del file originale OPPURE del file archiviato
    keys = [k for k in ingested if "Test meeting" in k]
    assert keys, f"manifest non contiene entry per il sorgente: {list(ingested.keys())}"
    entry = ingested[keys[0]]
    assert "hash" in entry
    assert "generated_note_hash" in entry

    # Source archiviato in note_riunioni/archive/2026-05/
    archive = source_dir / "archive" / "2026-05"
    assert archive.exists()
    assert list(archive.glob("*.md"))
