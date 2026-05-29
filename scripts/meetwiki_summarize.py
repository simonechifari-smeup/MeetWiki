"""
MeetWiki summarize — genera pagine aggregate in topics/{tag}.md e people/{slug}.md
per tag/persone con almeno N riunioni.
Conforme alla skill .github/skills/meetwiki-summarize/SKILL.md.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "MeetWiki"
NOTES = WIKI / "notes"
TOPICS = WIKI / "topics"
PEOPLE = WIKI / "people"

MIN_NOTES = 2  # soglia minima per generare la pagina aggregata

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meetwiki_common import (  # noqa: E402
    parse_frontmatter as _common_parse_frontmatter,
    slugify as _common_slugify,
    extract_section,
)


def slugify(text: str) -> str:
    return _common_slugify(text)


def parse_note(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    fm, body = _common_parse_frontmatter(text)
    if not fm.get("id"):
        return None
    rel = path.relative_to(NOTES).as_posix()
    fm["_path_topics"] = f"../notes/{rel}"
    fm["_path_people"] = f"../notes/{rel}"
    fm["_body"] = body
    return fm


def get_summary(fm: dict) -> str:
    s = extract_section(fm["_body"], "Riepilogo")
    s = re.sub(r"_Nessun riepilogo.*_", "", s).strip()
    return s


def get_open_actions(fm: dict) -> list[str]:
    section = extract_section(fm["_body"], "Action Items")
    items = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("- [ ]"):
            items.append(line)
    return items


def short_summary(fm: dict, max_chars: int = 280) -> str:
    s = get_summary(fm)
    if not s:
        return "_Nessun riepilogo._"
    # Prima frase / primo paragrafo
    first = re.split(r"\n\n|\.\s", s, maxsplit=1)[0]
    if len(first) > max_chars:
        first = first[:max_chars].rsplit(" ", 1)[0] + "..."
    return first.rstrip(".") + "."


def render_topic(tag: str, notes: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    notes_sorted = sorted(notes, key=lambda n: n["date"], reverse=True)
    # Statistiche
    people_counter: Counter = Counter()
    for n in notes:
        for p in n.get("participants") or []:
            people_counter[p] += 1
    top_people = people_counter.most_common(8)

    all_actions: list[tuple[str, dict]] = []
    for n in notes_sorted:
        for a in get_open_actions(n):
            all_actions.append((a, n))

    lines = [
        "---",
        "type: topic",
        f"tag: {tag}",
        f"generated_at: {now}",
        f"notes_count: {len(notes)}",
        "---",
        "",
        f"# Topic: {tag}",
        "",
        f"#{tag}",
        "",
        "> [!info] Sintesi globale",
        f"> Argomento ricorrente in **{len(notes)} riunioni** "
        f"({notes_sorted[-1]['date']} → {notes_sorted[0]['date']}).",
        "",
    ]
    if top_people:
        lines.append("**Partecipanti principali:** " +
                     ", ".join(f"{p} ({c})" for p, c in top_people))
        lines.append("")
    lines += ["## Riepiloghi per riunione", ""]
    for n in notes_sorted:
        lines.append(f"### {n['date']} — [{n['title']}]({n['_path_topics']})")
        lines.append("")
        lines.append(short_summary(n))
        lines.append("")
    lines += ["## Action items aperti", ""]
    if all_actions:
        lines.append("> [!todo] Aperti")
        for action, n in all_actions:
            lines.append(f"> - {action[5:].strip()}  ")
            lines.append(f">   _da [{n['date']} — {n['title']}]({n['_path_topics']})_")
    else:
        lines.append("_Nessun action item aperto._")
    lines += ["", "## Note correlate (cronologico)", ""]
    for n in notes_sorted:
        lines.append(f"- {n['date']} — [{n['title']}]({n['_path_topics']})")
    return "\n".join(lines) + "\n"


def render_person(name: str, notes: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    notes_sorted = sorted(notes, key=lambda n: n["date"], reverse=True)
    slug = slugify(name)
    # Tag più frequenti
    tag_counter: Counter = Counter()
    for n in notes:
        for t in n.get("tags") or []:
            tag_counter[t] += 1
    top_tags = tag_counter.most_common(10)

    # Action items dove la persona è menzionata
    own_actions: list[tuple[str, dict]] = []
    name_low = name.lower()
    first_name = name.split()[0].lower() if name.split() else name_low
    for n in notes_sorted:
        for a in get_open_actions(n):
            al = a.lower()
            if name_low in al or first_name in al:
                own_actions.append((a, n))

    lines = [
        "---",
        "type: person",
        f"name: \"{name}\"",
        f"slug: {slug}",
        f"generated_at: {now}",
        f"meetings_count: {len(notes)}",
        "---",
        "",
        f"# {name}",
        "",
        "> [!info] Partecipa a "
        f"**{len(notes)} riunioni** "
        f"({notes_sorted[-1]['date']} → {notes_sorted[0]['date']}).",
        "",
        "## Aree di attività",
        "",
    ]
    if top_tags:
        # Tag inline cliccabili in Obsidian + leggibili su GitHub
        lines.append(" ".join(f"#{t}" for t, _ in top_tags))
        lines.append("")
        lines.append(", ".join(f"`{t}` ({c})" for t, c in top_tags))
    else:
        lines.append("_Nessun tag aggregato._")
    lines += ["", "## Action items potenzialmente assegnati", ""]
    if own_actions:
        lines.append("> [!todo] Aperti")
        for action, n in own_actions:
            lines.append(f"> - {action[5:].strip()}  ")
            lines.append(f">   _da [{n['date']} — {n['title']}]({n['_path_people']})_")
    else:
        lines.append("_Nessun action item rilevato._")
    lines += ["", "## Riunioni (cronologico)", ""]
    for n in notes_sorted:
        lines.append(f"- {n['date']} — [{n['title']}]({n['_path_people']})")
    return "\n".join(lines) + "\n"


def main() -> int:
    TOPICS.mkdir(parents=True, exist_ok=True)
    PEOPLE.mkdir(parents=True, exist_ok=True)

    notes = []
    for p in sorted(NOTES.rglob("*.md")):
        if any(part.startswith("_") for part in p.relative_to(NOTES).parts):
            continue
        n = parse_note(p)
        if n:
            notes.append(n)

    # Aggregazioni
    by_tag: dict = defaultdict(list)
    by_person: dict = defaultdict(list)
    for n in notes:
        for t in n.get("tags") or []:
            by_tag[t].append(n)
        for pp in n.get("participants") or []:
            by_person[pp].append(n)

    topic_files = 0
    for tag, group in by_tag.items():
        if len(group) < MIN_NOTES:
            continue
        out = TOPICS / f"{tag}.md"
        out.write_text(render_topic(tag, group), encoding="utf-8")
        topic_files += 1

    person_files = 0
    for person, group in by_person.items():
        if len(group) < MIN_NOTES:
            continue
        out = PEOPLE / f"{slugify(person)}.md"
        out.write_text(render_person(person, group), encoding="utf-8")
        person_files += 1

    skipped_tags = sum(1 for g in by_tag.values() if len(g) < MIN_NOTES)
    skipped_people = sum(1 for g in by_person.values() if len(g) < MIN_NOTES)
    print(f"Topic generati: {topic_files} (saltati {skipped_tags} con <{MIN_NOTES} note).")
    print(f"Persone generate: {person_files} (saltate {skipped_people} con <{MIN_NOTES} riunioni).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
