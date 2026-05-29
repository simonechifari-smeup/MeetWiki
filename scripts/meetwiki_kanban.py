"""
MeetWiki kanban — board interattive Obsidian (plugin mgmeyers/obsidian-kanban)
per gli action items, con sync bidirezionale verso `.meta/actions_status.json`.

Genera:
- MeetWiki/MY-KANBAN.md            (board personale dell'owner principale)
- MeetWiki/actions/kanban/{slug}.md (una board per ogni altro owner, opzionale)

Comandi:
    python scripts/meetwiki_kanban.py --export         # rigenera le board dallo stato
    python scripts/meetwiki_kanban.py --sync           # legge le board e aggiorna lo stato
    python scripts/meetwiki_kanban.py --sync --export  # sync poi re-export (pipeline)
    python scripts/meetwiki_kanban.py --me-only        # genera solo MY-KANBAN.md

Owner principale: variabile `MEETWIKI_OWNER` in .env (default: persona piu' frequente).

Formato card:
    - [ ] {task}  [↗](../notes/2026-05/x.md) ^h{hash10}

Colonne:
    Open | In Progress | Blocked | Done

Conforme alla skill .github/skills/meetwiki-kanban/SKILL.md.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "MeetWiki"
NOTES = WIKI / "notes"
KANBAN_DIR = WIKI / "actions" / "kanban"
MY_KANBAN = WIKI / "MY-KANBAN.md"
STATUS_FILE = WIKI / ".meta" / "actions_status.json"
ENV_FILE = ROOT / ".env"

# Riusa il parser/estrattore di meetwiki_actions.py per non duplicare logica.
sys.path.insert(0, str(ROOT / "scripts"))
from meetwiki_actions import collect_actions, slugify  # noqa: E402

COLUMNS = ["Open", "In Progress", "Blocked", "Done"]
STATUS_TO_COL = {"open": "Open", "in_progress": "In Progress",
                 "blocked": "Blocked", "done": "Done"}
COL_TO_STATUS = {v: k for k, v in STATUS_TO_COL.items()}

CARD_RE = re.compile(
    r"^- \[([ xX])\]\s+(.*?)\s+\^h([a-f0-9]{10})\s*$"
)
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
KANBAN_SETTINGS = (
    "%% kanban:settings\n"
    "```\n"
    '{"kanban-plugin":"board","show-checkboxes":true,'
    '"date-display-format":"YYYY-MM-DD","link-date-to-daily-note":false}\n'
    "```\n"
    "%%\n"
)


def load_env_owner() -> str | None:
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("MEETWIKI_OWNER="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def detect_owner(items: list[dict]) -> str:
    """Owner principale: env var MEETWIKI_OWNER, altrimenti il piu' frequente."""
    env = load_env_owner() or os.environ.get("MEETWIKI_OWNER")
    if env:
        return env
    if not items:
        return "Non assegnato"
    counter: Counter = Counter()
    for it in items:
        counter[it["owner"]] += 1
    return counter.most_common(1)[0][0]


# --- EXPORT: stato JSON -> file Kanban ---

def card_line(item: dict) -> str:
    """Una riga card del Kanban, con link relativo e blockref hash come ancora."""
    # Path relativo da WIKI (es. "notes/2026-05/x.md").
    # Le board sono in: WIKI/MY-KANBAN.md o WIKI/actions/kanban/{slug}.md
    # Il path che stampiamo nella card va calcolato in chi chiama (per usare il giusto prefisso).
    raise NotImplementedError  # sostituita da render_card


def render_card(item: dict, from_board: Path) -> str:
    """Card markdown relativa a `from_board`."""
    note_abs = WIKI / item["note_path"]
    rel = os.path.relpath(note_abs, from_board.parent).replace("\\", "/")
    check = "x" if item["status"] == "done" else " "
    # Tronca task lunghi a una riga (Obsidian Kanban gestisce wrap)
    task = item["task"].replace("\n", " ").strip()
    return f"- [{check}] {task}  [↗]({rel}) ^h{item['hash']}"


def render_board(title: str, items: list[dict], board_path: Path,
                 subtitle: str | None = None) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    by_col: dict = defaultdict(list)
    for it in items:
        col = STATUS_TO_COL.get(it["status"], "Open")
        by_col[col].append(it)

    # Ordina: per data desc dentro ogni colonna
    for col in by_col:
        by_col[col].sort(key=lambda i: i["date"], reverse=True)

    lines = [
        "---",
        "",
        "kanban-plugin: board",
        f"generated_at: {now}",
        "",
        "---",
        "",
        f"# {title}",
        "",
    ]
    if subtitle:
        lines.append(f"> {subtitle}")
        lines.append("")

    for col in COLUMNS:
        lines.append(f"## {col}")
        lines.append("")
        if col == "Done":
            lines.append("**Complete**")
            lines.append("")
        cards = by_col.get(col, [])
        for it in cards:
            lines.append(render_card(it, board_path))
        if not cards:
            lines.append("")  # colonna vuota: ok per il plugin
        lines.append("")

    lines.append("")
    lines.append(KANBAN_SETTINGS)
    return "\n".join(lines)


def export_boards(items: list[dict], owner: str,
                  me_only: bool = False) -> tuple[int, Path]:
    KANBAN_DIR.mkdir(parents=True, exist_ok=True)

    # Board personale: match esatto sugli owner splittati
    owner_l = owner.lower()
    owner_first = owner.split()[0].lower() if owner.split() else owner_l

    def is_mine(it: dict) -> bool:
        for o in it.get("owners", [it["owner"]]):
            ol = o.lower()
            if ol == owner_l or owner_l in ol or ol.split()[0] == owner_first:
                return True
        return False

    my_items = [i for i in items if is_mine(i)]
    subtitle = (f"Action items assegnati a **{owner}** "
                f"({sum(1 for i in my_items if i['status']=='open')} aperti / "
                f"{len(my_items)} totali). "
                f"Drag&drop tra colonne per cambiare stato, poi "
                f"`meetwiki_kanban.py --sync`.")
    MY_KANBAN.write_text(
        render_board(f"My Kanban — {owner}", my_items, MY_KANBAN, subtitle),
        encoding="utf-8")

    n_boards = 1
    if not me_only:
        # Pulisci board per-owner stale e rigenera
        for old in KANBAN_DIR.glob("*.md"):
            old.unlink()
        by_owner: dict = defaultdict(list)
        for it in items:
            for o in it.get("owners", [it["owner"]]):
                by_owner[o].append(it)
        for own, group in by_owner.items():
            if is_mine({"owners": [own], "owner": own}):
                continue  # gia' nella MY-KANBAN
            slug = slugify(own)
            out = KANBAN_DIR / f"{slug}.md"
            sub = (f"Action items di **{own}** "
                   f"({sum(1 for i in group if i['status']=='open')} aperti).")
            out.write_text(render_board(f"Kanban — {own}", group, out, sub),
                           encoding="utf-8")
            n_boards += 1
    return n_boards, MY_KANBAN


# --- SYNC: file Kanban -> stato JSON ---

def parse_board(path: Path) -> dict[str, str]:
    """Ritorna {hash: status} letto dalla board."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    current_col: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        # Ignora frontmatter, settings, complete-marker
        if line.startswith("## "):
            heading = HEADING_RE.match(line)
            if heading:
                current_col = heading.group(1).strip()
            continue
        if current_col is None:
            continue
        m = CARD_RE.match(line.strip())
        if not m:
            continue
        check, _task, h = m.group(1), m.group(2), m.group(3)
        status = COL_TO_STATUS.get(current_col)
        if status is None:
            # Colonna non riconosciuta: deriva da checkbox
            status = "done" if check.lower() == "x" else "open"
        out[h] = status
    return out


def load_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_status(data: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                           encoding="utf-8")


def sync_boards(items_by_hash: dict[str, dict]) -> tuple[int, int]:
    """Legge MY-KANBAN.md + actions/kanban/*.md e aggiorna actions_status.json.
    Ritorna (n_card_lette, n_status_modificati)."""
    boards = [MY_KANBAN] + sorted(KANBAN_DIR.glob("*.md"))
    seen: dict[str, str] = {}
    for b in boards:
        for h, st in parse_board(b).items():
            seen[h] = st  # ultima board vince (MY-KANBAN ha la priorita' bassa)

    status = load_status()
    today = datetime.now().strftime("%Y-%m-%d")
    n_changed = 0
    for h, new_st in seen.items():
        # Default base (origine dalle note): se la nota e' "- [ ]" lo status base e' open
        current = status.get(h, {})
        cur_st = current.get("status", "open")
        if new_st == cur_st:
            continue
        # Update
        entry = dict(current)
        entry["status"] = new_st
        if new_st == "done":
            entry.setdefault("closed_at", today)
            entry.setdefault("note", "Chiuso da Kanban")
        else:
            # riaperto / spostato: rimuovi closed_at
            entry.pop("closed_at", None)
        status[h] = entry
        n_changed += 1

    # Cleanup: rimuovi voci orfane (hash non piu' presenti in nessuna nota)
    orphans = [h for h in status.keys() if h not in items_by_hash and h not in seen]
    for h in orphans:
        del status[h]

    save_status(status)
    return len(seen), n_changed


# --- Main ---

def main() -> int:
    do_sync = "--sync" in sys.argv
    do_export = "--export" in sys.argv
    me_only = "--me-only" in sys.argv
    if not do_sync and not do_export:
        # default: sync + export (pipeline-safe)
        do_sync = True
        do_export = True

    items = collect_actions()
    items_by_hash = {i["hash"]: i for i in items}
    owner = detect_owner(items)

    if do_sync:
        n_seen, n_changed = sync_boards(items_by_hash)
        print(f"[SYNC] {n_seen} card lette, {n_changed} status aggiornati in actions_status.json")
        if n_changed:
            # Ricarica items con nuovo status
            items = collect_actions()

    if do_export:
        n_boards, my_path = export_boards(items, owner, me_only=me_only)
        my_rel = my_path.relative_to(WIKI).as_posix()
        print(f"[EXPORT] {n_boards} board generate. Owner principale: {owner}. "
              f"Personale -> {my_rel}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
