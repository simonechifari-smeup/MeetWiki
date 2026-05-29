"""
MeetWiki actions — aggrega gli action items di tutte le note in
MeetWiki/ACTIONS.md (vista globale) + actions/by-owner/{slug}.md (per persona).

Stato:
- Default: tutti gli action items sono `open`.
- Override manuale in MeetWiki/.meta/actions_status.json con schema:
    { "<action_hash>": { "status": "done", "closed_at": "YYYY-MM-DD", "note": "..." } }
  L'hash si ottiene da `meetwiki_actions.py --list` (stampato a fianco).

Conforme alla skill .github/skills/meetwiki-actions/SKILL.md.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "MeetWiki"
NOTES = WIKI / "notes"
ACTIONS_DIR = WIKI / "actions"
BY_OWNER_DIR = ACTIONS_DIR / "by-owner"
STATUS_FILE = WIKI / ".meta" / "actions_status.json"
GLOBAL_FILE = WIKI / "ACTIONS.md"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)", re.DOTALL)
# `- [ ] [Owner] task...`  oppure  `- [ ] \[Owner\] task...`  oppure  `- [ ] Owner: task...`
ACTION_CHECK_RE = re.compile(r"^- \[([ xX])\]\s*(.+)$")
ACTION_OWNER_BRACKET_RE = re.compile(r"^\\?\[([^\]\\]+?)\\?\]\s*[:\-]?\s+(.+)$")
ACTION_OWNER_COLON_RE = re.compile(r"^([A-ZÀ-Ý][\w' .-]{1,40}?):\s+(.+)$")

# Owner multipli: "Andrea Bortolan, Filippo Premoli" / "Andrea e Filippo" / "A & B"
OWNER_SEPARATORS_RE = re.compile(r"\s*(?:,|;|/|\s+e\s+|\s+&\s+|\s+\+\s+)\s*", re.IGNORECASE)
# Owner collettivi che NON vanno splittati ne' mappati su persone
GROUP_OWNERS = {"non assegnato", "il gruppo", "tutti", "team", "tbd", "da definire"}


def split_owners(owner: str) -> list[str]:
    """Splitta un owner string in lista di persone individuali.
    `'A, B e C'` -> `['A', 'B', 'C']`. Lascia intatti i collettivi (`'Il gruppo'`)."""
    if not owner:
        return ["Non assegnato"]
    raw = owner.strip()
    if raw.lower() in GROUP_OWNERS:
        return [raw]
    parts = [p.strip() for p in OWNER_SEPARATORS_RE.split(raw) if p.strip()]
    parts = [p for p in parts if len(p) >= 2]
    return parts or [raw]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "anonimo"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict = {}
    list_key = None
    for line in m.group(1).splitlines():
        if line.startswith("  - ") and list_key:
            fm.setdefault(list_key, []).append(line[4:].strip().strip('"'))
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip(); v = v.strip()
            if v == "":
                fm[k] = []; list_key = k
            elif v == "[]":
                fm[k] = []; list_key = None
            else:
                fm[k] = v.strip('"'); list_key = None
    return fm, m.group(2)


def extract_section(body: str, heading: str) -> str:
    pat = re.compile(rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)",
                     re.MULTILINE | re.DOTALL)
    m = pat.search(body)
    return m.group(1).strip() if m else ""


def action_hash(owner: str, task: str, note_id: str) -> str:
    """ID stabile di un action item: deterministico su owner+task+nota origine."""
    key = f"{note_id}|{owner.lower().strip()}|{task.lower().strip()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def load_status() -> dict:
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return {}


def collect_actions() -> list[dict]:
    """Ritorna lista di {hash, owner, task, date, note_id, note_title, note_path,
    status, closed_at, status_note}."""
    status = load_status()
    items: list[dict] = []
    for p in sorted(NOTES.rglob("*.md")):
        if any(part.startswith("_") for part in p.relative_to(NOTES).parts):
            continue
        fm, body = parse_frontmatter(p.read_text(encoding="utf-8"))
        if not fm.get("id"):
            continue
        section = extract_section(body, "Action Items")
        if not section:
            continue
        rel = p.relative_to(WIKI).as_posix()  # "notes/2026-05/xxx.md"
        for raw_line in section.splitlines():
            line = raw_line.strip()
            if not line.startswith("- ["):
                continue
            cm = ACTION_CHECK_RE.match(line)
            if not cm:
                continue
            check, rest = cm.group(1), cm.group(2).strip()
            bm = ACTION_OWNER_BRACKET_RE.match(rest)
            if bm:
                owner, task = bm.group(1), bm.group(2)
            else:
                cmo = ACTION_OWNER_COLON_RE.match(rest)
                if cmo:
                    owner, task = cmo.group(1), cmo.group(2)
                else:
                    owner, task = "Non assegnato", rest
            owner = owner.replace("\\", "").strip()
            task = task.replace("\\[", "[").replace("\\]", "]").strip()
            h = action_hash(owner, task, fm["id"])
            override = status.get(h, {})
            inline_done = check.lower() == "x"
            st = override.get("status") or ("done" if inline_done else "open")
            items.append({
                "hash": h,
                "owner": owner,
                "owners": split_owners(owner),
                "task": task,
                "date": fm.get("date", ""),
                "note_id": fm["id"],
                "note_title": fm.get("title", fm["id"]),
                "note_path": rel,
                "status": st,
                "closed_at": override.get("closed_at", ""),
                "status_note": override.get("note", ""),
            })
    return items


def _link(rel_note: str, from_dir: Path) -> str:
    """Relative link da `from_dir` alla nota `rel_note` (relativa a WIKI)."""
    target = WIKI / rel_note
    try:
        return target.relative_to(from_dir, walk_up=True).as_posix()  # Py 3.12+
    except (ValueError, TypeError):
        # Fallback: calcola a mano
        import os
        return Path(os.path.relpath(target, from_dir)).as_posix()


def render_global(items: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    open_items = [i for i in items if i["status"] == "open"]
    done_items = [i for i in items if i["status"] == "done"]
    by_owner_open: dict = defaultdict(list)
    for i in open_items:
        for o in i["owners"]:
            by_owner_open[o].append(i)

    lines = [
        "---",
        "type: actions-global",
        f"generated_at: {now}",
        f"total: {len(items)}",
        f"open: {len(open_items)}",
        f"done: {len(done_items)}",
        "---",
        "",
        "# Action Items — Vista globale",
        "",
        f"> Generato da `meetwiki-actions` il {now}. "
        f"Per chiudere un task: aggiungi l'hash a `.meta/actions_status.json`.",
        "",
        f"**Totale:** {len(items)} — **Aperti:** {len(open_items)} — **Chiusi:** {len(done_items)}",
        "",
        "## Aperti per persona",
        "",
    ]
    if not by_owner_open:
        lines.append("_Nessun action item aperto._")
    else:
        for owner in sorted(by_owner_open.keys(),
                            key=lambda o: (-len(by_owner_open[o]), o)):
            group = sorted(by_owner_open[owner], key=lambda i: i["date"], reverse=True)
            lines.append(f"### {owner} ({len(group)})")
            for i in group:
                lines.append(
                    f"- `{i['hash']}` — {i['task']}  \n"
                    f"  _{i['date']} — [{i['note_title']}]({i['note_path']})_"
                )
            lines.append("")

    lines += ["## Chiusi (recenti)", ""]
    if not done_items:
        lines.append("_Nessun action item chiuso._")
    else:
        recent = sorted(done_items,
                        key=lambda i: i["closed_at"] or i["date"], reverse=True)[:30]
        for i in recent:
            closed = i["closed_at"] or "?"
            lines.append(
                f"- ~~{i['owner']} — {i['task']}~~  \n"
                f"  _chiuso {closed} · da [{i['note_title']}]({i['note_path']})_"
            )
    lines += ["", "---", "",
              "## Come chiudere un action item",
              "",
              "1. Copia l'hash a 10 caratteri (es. `a1b2c3d4e5`)",
              "2. Apri `MeetWiki/.meta/actions_status.json`",
              "3. Aggiungi una entry:",
              "",
              "```json",
              "{",
              '  "a1b2c3d4e5": { "status": "done", "closed_at": "2026-05-29", "note": "Completato in PR #123" }',
              "}",
              "```",
              "",
              "4. Ri-esegui `meetwiki_actions.py` (o `meetwiki_update.py`).",
              ]
    return "\n".join(lines) + "\n"


def render_owner(owner: str, items: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    open_items = sorted([i for i in items if i["status"] == "open"],
                        key=lambda i: i["date"], reverse=True)
    done_items = sorted([i for i in items if i["status"] == "done"],
                        key=lambda i: i["closed_at"] or i["date"], reverse=True)
    slug = slugify(owner)

    def link(rel: str) -> str:
        # da actions/by-owner/X.md  ->  ../../notes/...
        return f"../../{rel}"

    lines = [
        "---",
        "type: actions-owner",
        f"owner: \"{owner}\"",
        f"slug: {slug}",
        f"generated_at: {now}",
        f"open: {len(open_items)}",
        f"done: {len(done_items)}",
        "---",
        "",
        f"# Action items — {owner}",
        "",
        f"**Aperti:** {len(open_items)} — **Chiusi:** {len(done_items)}",
        "",
        "## Aperti",
        "",
    ]
    if not open_items:
        lines.append("_Nessun action item aperto._")
    else:
        for i in open_items:
            co = [o for o in i.get("owners", []) if o != owner]
            co_s = f" · con {', '.join(co)}" if co else ""
            lines.append(
                f"- `{i['hash']}` — {i['task']}  \n"
                f"  _{i['date']} — [{i['note_title']}]({link(i['note_path'])}){co_s}_"
            )

    lines += ["", "## Chiusi", ""]
    if not done_items:
        lines.append("_Nessun action item chiuso._")
    else:
        for i in done_items:
            closed = i["closed_at"] or "?"
            extra = f" — {i['status_note']}" if i["status_note"] else ""
            lines.append(
                f"- ~~{i['task']}~~ _(chiuso {closed}{extra})_  \n"
                f"  _da [{i['note_title']}]({link(i['note_path'])})_"
            )
    return "\n".join(lines) + "\n"


def _purge_owner_dir() -> None:
    if not BY_OWNER_DIR.exists():
        return
    for p in BY_OWNER_DIR.glob("*.md"):
        p.unlink()


def main() -> int:
    if "--list" in sys.argv:
        items = collect_actions()
        for i in items:
            mark = "x" if i["status"] == "done" else " "
            print(f"[{mark}] {i['hash']}  {i['date']}  {i['owner']:<30}  {i['task'][:80]}")
        print(f"\nTotale: {len(items)} (aperti: {sum(1 for i in items if i['status']=='open')})")
        return 0

    ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    BY_OWNER_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STATUS_FILE.exists():
        STATUS_FILE.write_text("{}\n", encoding="utf-8")

    items = collect_actions()
    GLOBAL_FILE.write_text(render_global(items), encoding="utf-8")

    by_owner: dict = defaultdict(list)
    for i in items:
        for o in i["owners"]:
            by_owner[o].append(i)

    _purge_owner_dir()
    for owner, group in by_owner.items():
        slug = slugify(owner)
        (BY_OWNER_DIR / f"{slug}.md").write_text(
            render_owner(owner, group), encoding="utf-8")

    open_n = sum(1 for i in items if i["status"] == "open")
    print(f"Action items: {len(items)} totali, {open_n} aperti, "
          f"{len(items)-open_n} chiusi. "
          f"Owner: {len(by_owner)}. File: ACTIONS.md + actions/by-owner/*.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
