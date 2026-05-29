"""
MeetWiki update — pipeline completa: ingest -> index -> summarize -> actions -> digest -> search index -> kanban.

Conforme alla skill .github/skills/meetwiki-update/SKILL.md.

Uso:
    python scripts/meetwiki_update.py            # update incrementale + sync Kanban
    python scripts/meetwiki_update.py --force    # re-ingest di tutte le note
    python scripts/meetwiki_update.py --clean    # svuota topics/ e people/ prima
    python scripts/meetwiki_update.py --reset    # distruttivo: pulisce tutto
    python scripts/meetwiki_update.py --skip-digest    # salta digest week/month
    python scripts/meetwiki_update.py --skip-search    # salta rebuild indice ricerca
    python scripts/meetwiki_update.py --skip-kanban    # salta sync+export board Obsidian
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
WIKI = ROOT / "MeetWiki"


def _purge(*globs: str) -> int:
    n = 0
    for pattern in globs:
        for p in WIKI.glob(pattern):
            if p.is_file():
                p.unlink()
                n += 1
    return n


def _purge_notes_tree() -> int:
    """Cancella tutte le note (anche in sottocartelle YYYY-MM) e lo storico,
    ma preserva la cartella `notes/` stessa."""
    notes_dir = WIKI / "notes"
    if not notes_dir.exists():
        return 0
    n = 0
    for p in notes_dir.rglob("*.md"):
        p.unlink()
        n += 1
    # Rimuovi sottodir vuote (incluso _history/YYYY-MM)
    for d in sorted((p for p in notes_dir.rglob("*") if p.is_dir()), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass
    return n


def _run(args: list[str]) -> None:
    print(f"\n=== {' '.join(args)} ===", flush=True)
    res = subprocess.run([sys.executable, *args], cwd=ROOT)
    if res.returncode != 0:
        raise SystemExit(f"step fallito ({args[0]}), exit={res.returncode}")


def main() -> int:
    p = argparse.ArgumentParser(
        prog="meetwiki-update",
        description="Pipeline MeetWiki completa: ingest -> index -> summarize -> actions -> digest -> search -> kanban.",
    )
    p.add_argument("--force", action="store_true", help="re-ingest di tutte le note")
    p.add_argument("--clean", action="store_true", help="svuota topics/, people/, digests/, actions/ prima")
    p.add_argument("--reset", action="store_true", help="distruttivo: pulisce tutto e re-ingest (implica --force)")
    p.add_argument("--skip-digest", action="store_true", help="salta digest settimanali/mensili")
    p.add_argument("--skip-search", action="store_true", help="salta rebuild indice ricerca")
    p.add_argument("--skip-kanban", action="store_true", help="salta sync+export board Obsidian")
    p.add_argument("--dry-run", action="store_true",
                   help="esegue solo l'ingest in modalita' dry-run (nessuna scrittura) e salta i passi successivi")
    a = p.parse_args()
    force = a.force
    clean = a.clean
    reset = a.reset
    skip_digest = a.skip_digest
    skip_search = a.skip_search
    skip_kanban = a.skip_kanban
    dry_run = a.dry_run

    if dry_run:
        ingest_args = [str(SCRIPTS / "meetwiki_ingest.py"), "--dry-run"]
        if force:
            ingest_args.append("--force")
        _run(ingest_args)
        print("\n[DRY-RUN] pipeline interrotta dopo ingest (nessuno step successivo eseguito).")
        return 0

    if reset:
        n = _purge_notes_tree()
        n += _purge("topics/*.md", "people/*.md",
                    "digests/weekly/*.md", "digests/monthly/*.md",
                    "actions/by-owner/*.md", "actions/kanban/*.md",
                    "ACTIONS.md", "MY-KANBAN.md")
        manifest = WIKI / ".meta" / "manifest.json"
        if manifest.exists():
            manifest.unlink()
            n += 1
        search_idx = WIKI / ".meta" / "search_index.json"
        if search_idx.exists():
            search_idx.unlink()
            n += 1
        print(f"[RESET] eliminati {n} file (manifest + notes/topics/people/digests/actions/kanban/search_index).")
        force = True
    elif clean:
        n = _purge("topics/*.md", "people/*.md",
                   "digests/weekly/*.md", "digests/monthly/*.md",
                   "actions/by-owner/*.md", "actions/kanban/*.md")
        print(f"[CLEAN] eliminati {n} file in topics/, people/, digests/, actions/.")

    # IMPORTANTE: sync Kanban PRIMA dell'ingest, per non perdere drag&drop
    # eventuali fatti dall'utente in Obsidian dall'ultimo update.
    if not skip_kanban:
        _run([str(SCRIPTS / "meetwiki_kanban.py"), "--sync"])

    ingest_args = [str(SCRIPTS / "meetwiki_ingest.py")]
    if force:
        ingest_args.append("--force")

    _run(ingest_args)
    _run([str(SCRIPTS / "meetwiki_index.py")])
    _run([str(SCRIPTS / "meetwiki_summarize.py")])
    _run([str(SCRIPTS / "meetwiki_actions.py")])

    if not skip_digest:
        _run([str(SCRIPTS / "meetwiki_digest.py"), "--all"])
        _run([str(SCRIPTS / "meetwiki_digest.py"), "--period", "month", "--all"])

    if not skip_search:
        _run([str(SCRIPTS / "meetwiki_ask.py"), "--index"])

    # Re-export Kanban DOPO actions (cosi' nuove card appaiono in board)
    if not skip_kanban:
        _run([str(SCRIPTS / "meetwiki_kanban.py"), "--export"])

    print("\nPipeline MeetWiki completata.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
