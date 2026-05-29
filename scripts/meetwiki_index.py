"""
MeetWiki index — rigenera INDEX.md, TAGS.md, PEOPLE.md.
Conforme alla skill .github/skills/meetwiki-index/SKILL.md.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "MeetWiki"
NOTES = WIKI / "notes"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meetwiki_common import parse_frontmatter as _common_parse_frontmatter  # noqa: E402

MONTHS_IT = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
             "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]


def parse_frontmatter(text: str) -> dict:
    fm, _ = _common_parse_frontmatter(text)
    return fm



def load_notes() -> list[dict]:
    items: list[dict] = []
    for p in sorted(NOTES.rglob("*.md")):
        # Salta _history/ e qualsiasi dir/file con prefisso underscore
        if any(part.startswith("_") for part in p.relative_to(NOTES).parts):
            continue
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        if not fm.get("id") or not fm.get("date"):
            print(f"WARN: frontmatter mancante in {p.name}", file=sys.stderr)
            continue
        rel = p.relative_to(NOTES).as_posix()
        fm["_path"] = f"notes/{rel}"
        items.append(fm)
    return items


def gen_index(notes: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = ["# Indice cronologico", "",
             f"> Generato da `meetwiki-index` il {now}. Non modificare a mano.", ""]
    by_year: dict = defaultdict(lambda: defaultdict(list))
    for n in notes:
        y, m, _ = n["date"].split("-")
        by_year[int(y)][int(m)].append(n)
    for year in sorted(by_year.keys(), reverse=True):
        lines.append(f"## {year}")
        lines.append("")
        for month in sorted(by_year[year].keys(), reverse=True):
            lines.append(f"### {MONTHS_IT[month-1]}")
            for n in sorted(by_year[year][month], key=lambda x: x["date"], reverse=True):
                lines.append(f"- {n['date']} — [{n['title']}]({n['_path']})")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def gen_tags(notes: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    by_tag: dict = defaultdict(list)
    for n in notes:
        for t in n.get("tags") or []:
            by_tag[t].append(n)
    lines = ["# Indice per tag", "",
             f"> Generato da `meetwiki-index` il {now}.", ""]
    for tag in sorted(by_tag.keys(), key=lambda t: (-len(by_tag[t]), t)):
        items = sorted(by_tag[tag], key=lambda n: n["date"], reverse=True)
        lines.append(f"## {tag} ({len(items)})")
        for n in items:
            lines.append(f"- {n['date']} — [{n['title']}]({n['_path']})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def gen_people(notes: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    by_person: dict = defaultdict(list)
    for n in notes:
        for p in n.get("participants") or []:
            by_person[p].append(n)
    lines = ["# Indice partecipanti", "",
             f"> Generato da `meetwiki-index` il {now}.", ""]
    for person in sorted(by_person.keys(), key=lambda p: (-len(by_person[p]), p)):
        items = sorted(by_person[person], key=lambda n: n["date"], reverse=True)
        lines.append(f"## {person} ({len(items)} riunioni)")
        for n in items:
            lines.append(f"- {n['date']} — [{n['title']}]({n['_path']})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    notes = load_notes()
    (WIKI / "INDEX.md").write_text(gen_index(notes), encoding="utf-8")
    (WIKI / "TAGS.md").write_text(gen_tags(notes), encoding="utf-8")
    (WIKI / "PEOPLE.md").write_text(gen_people(notes), encoding="utf-8")
    tags_count = len({t for n in notes for t in (n.get("tags") or [])})
    people_count = len({p for n in notes for p in (n.get("participants") or [])})
    print(f"Indici rigenerati: {len(notes)} note, {tags_count} tag, {people_count} persone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
