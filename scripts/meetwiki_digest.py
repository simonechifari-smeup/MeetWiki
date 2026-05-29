"""
MeetWiki digest — genera digest periodici (settimanali e mensili) delle riunioni.

Output:
- MeetWiki/digests/weekly/YYYY-Www.md    (default)
- MeetWiki/digests/monthly/YYYY-MM.md    (--period month)

Uso:
    python scripts/meetwiki_digest.py                          # settimana corrente
    python scripts/meetwiki_digest.py --period month           # mese corrente
    python scripts/meetwiki_digest.py --date 2026-05-20        # settimana che contiene quella data
    python scripts/meetwiki_digest.py --period month --date 2026-04-15
    python scripts/meetwiki_digest.py --all                    # rigenera TUTTI i digest storici
    python scripts/meetwiki_digest.py --period month --all

Conforme alla skill .github/skills/meetwiki-digest/SKILL.md.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "MeetWiki"
NOTES = WIKI / "notes"
DIGESTS = WIKI / "digests"
WEEKLY = DIGESTS / "weekly"
MONTHLY = DIGESTS / "monthly"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meetwiki_common import extract_section, parse_frontmatter  # noqa: E402

MONTHS_IT = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
             "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]



def short_summary(body: str, max_chars: int = 220) -> str:
    s = extract_section(body, "Riepilogo")
    s = re.sub(r"_Nessun riepilogo.*_", "", s).strip()
    if not s:
        return ""
    first = re.split(r"\n\n|\.\s", s, maxsplit=1)[0].strip()
    if len(first) > max_chars:
        first = first[:max_chars].rsplit(" ", 1)[0] + "..."
    return first.rstrip(".") + "."


def load_all_notes() -> list[dict]:
    items: list[dict] = []
    for p in sorted(NOTES.rglob("*.md")):
        if any(part.startswith("_") for part in p.relative_to(NOTES).parts):
            continue
        fm, body = parse_frontmatter(p.read_text(encoding="utf-8"))
        if not fm.get("id") or not fm.get("date"):
            continue
        try:
            d = datetime.strptime(fm["date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        fm["_date_obj"] = d
        fm["_body"] = body
        fm["_path"] = p.relative_to(WIKI).as_posix()  # "notes/2026-05/xxx.md"
        items.append(fm)
    return items


# --- Periodi ---

def week_range(d: date) -> tuple[date, date, str]:
    """Restituisce (lunedi, domenica, label 'YYYY-Www' ISO)."""
    iso_year, iso_week, iso_dow = d.isocalendar()
    monday = d - timedelta(days=iso_dow - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday, f"{iso_year}-W{iso_week:02d}"


def month_range(d: date) -> tuple[date, date, str]:
    start = d.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1) - timedelta(days=1)
    else:
        end = start.replace(month=start.month + 1) - timedelta(days=1)
    return start, end, f"{start.year}-{start.month:02d}"


def filter_period(notes: list[dict], start: date, end: date) -> list[dict]:
    return sorted([n for n in notes if start <= n["_date_obj"] <= end],
                  key=lambda n: n["_date_obj"])


# --- Estrazione highlights ---

def extract_actions_from_note(n: dict) -> list[tuple[str, str]]:
    """Ritorna lista di (status, raw_line) per gli action items della nota."""
    section = extract_section(n["_body"], "Action Items")
    out = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("- [ ]"):
            out.append(("open", line))
        elif line.startswith("- [x]") or line.startswith("- [X]"):
            out.append(("done", line))
    return out


# --- Rendering ---

def fmt_date_it(d: date) -> str:
    return f"{d.day} {MONTHS_IT[d.month-1][:3].lower()}"


def render_digest(period_label: str, period_human: str,
                  start: date, end: date, notes: list[dict],
                  all_notes_sorted: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    n_notes = len(notes)

    tags_counter: Counter = Counter()
    people_counter: Counter = Counter()
    new_actions: list[tuple[str, dict]] = []
    closed_actions: list[tuple[str, dict]] = []
    for n in notes:
        for t in n.get("tags") or []:
            tags_counter[t] += 1
        for p in n.get("participants") or []:
            people_counter[p] += 1
        for status, line in extract_actions_from_note(n):
            if status == "open":
                new_actions.append((line, n))
            else:
                closed_actions.append((line, n))

    # Confronto con periodo precedente: variazione tag
    prev_start = start - (end - start) - timedelta(days=1)
    prev_end = start - timedelta(days=1)
    prev_notes = [x for x in all_notes_sorted if prev_start <= x["_date_obj"] <= prev_end]
    prev_tags: Counter = Counter()
    for n in prev_notes:
        for t in n.get("tags") or []:
            prev_tags[t] += 1

    lines = [
        "---",
        "type: digest",
        f"period: {period_label}",
        f"period_start: {start.isoformat()}",
        f"period_end: {end.isoformat()}",
        f"generated_at: {now}",
        f"meetings_count: {n_notes}",
        "---",
        "",
        f"# Digest {period_human}",
        "",
        f"> {fmt_date_it(start)} → {fmt_date_it(end)} "
        f"({start.isoformat()} / {end.isoformat()})",
        "",
        f"**{n_notes} riunioni**, **{len(people_counter)} persone coinvolte**, "
        f"**{len(tags_counter)} aree tematiche**, "
        f"**{len(new_actions)} action items nuovi**, "
        f"**{len(closed_actions)} chiusi**.",
        "",
    ]

    if not notes:
        lines += ["_Nessuna riunione in questo periodo._", ""]
        return "\n".join(lines) + "\n"

    # --- Riunioni
    lines += ["## Riunioni", ""]
    for n in notes:
        rel = f"../../{n['_path']}"
        tags = ", ".join(f"`{t}`" for t in (n.get("tags") or []))
        meta = f" — {tags}" if tags else ""
        lines.append(f"- **{n['_date_obj'].isoformat()}** — [{n['title']}]({rel}){meta}")
        summ = short_summary(n["_body"])
        if summ:
            lines.append(f"  > {summ}")
    lines.append("")

    # --- Action items nuovi
    lines += [f"## Action items nuovi ({len(new_actions)})", ""]
    if new_actions:
        for line, n in new_actions[:50]:
            rel = f"../../{n['_path']}"
            lines.append(f"{line}  \n  _da [{n['date']} — {n['title']}]({rel})_")
        if len(new_actions) > 50:
            lines.append(f"\n_... e altri {len(new_actions)-50}._")
    else:
        lines.append("_Nessuno._")
    lines.append("")

    # --- Action items chiusi
    lines += [f"## Action items chiusi ({len(closed_actions)})", ""]
    if closed_actions:
        for line, n in closed_actions[:30]:
            rel = f"../../{n['_path']}"
            lines.append(f"{line}  \n  _da [{n['date']} — {n['title']}]({rel})_")
    else:
        lines.append("_Nessuno._")
    lines.append("")

    # --- Tag attivi (con delta)
    lines += ["## Tag più attivi", ""]
    if tags_counter:
        rows = []
        for tag, count in tags_counter.most_common():
            prev = prev_tags.get(tag, 0)
            delta = count - prev
            arrow = "→" if delta == 0 else ("↑" if delta > 0 else "↓")
            rows.append(f"- `{tag}` — {count} ({arrow}{abs(delta)} vs periodo precedente)")
        lines.extend(rows)
    else:
        lines.append("_Nessun tag._")
    lines.append("")

    # --- Persone più coinvolte
    lines += ["## Persone più coinvolte", ""]
    if people_counter:
        for person, count in people_counter.most_common(15):
            lines.append(f"- **{person}** — {count} riunioni")
    else:
        lines.append("_Nessuna persona estratta._")

    return "\n".join(lines) + "\n"


# --- Driver ---

def generate_one(period: str, target_date: date, all_notes: list[dict]) -> Path:
    if period == "week":
        start, end, label = week_range(target_date)
        human = f"settimana {label}"
        out_dir = WEEKLY
    else:
        start, end, label = month_range(target_date)
        human = f"{MONTHS_IT[start.month-1]} {start.year}"
        out_dir = MONTHLY

    out_dir.mkdir(parents=True, exist_ok=True)
    notes_in = filter_period(all_notes, start, end)
    content = render_digest(label, human, start, end, notes_in, all_notes)
    out = out_dir / f"{label}.md"
    out.write_text(content, encoding="utf-8")
    return out


def all_periods(period: str, all_notes: list[dict]) -> list[date]:
    """Restituisce un punto-data per ciascun periodo che ha almeno una nota."""
    seen: set[str] = set()
    out: list[date] = []
    for n in all_notes:
        d = n["_date_obj"]
        if period == "week":
            _, _, label = week_range(d)
        else:
            _, _, label = month_range(d)
        if label in seen:
            continue
        seen.add(label)
        out.append(d)
    return out


def parse_args(argv: list[str]) -> tuple[str, date | None, bool]:
    p = argparse.ArgumentParser(
        prog="meetwiki-digest",
        description="Genera digest periodici delle riunioni (settimanali/mensili).",
    )
    p.add_argument("--period", choices=("week", "month"), default="week",
                   help="granularita' del digest (default: week)")
    p.add_argument("--date", dest="date_s", default=None,
                   help="data target YYYY-MM-DD (default: oggi)")
    p.add_argument("--all", dest="do_all", action="store_true",
                   help="rigenera tutti i digest storici per il periodo scelto")
    a = p.parse_args(argv)
    target: date | None = None
    if a.date_s is not None:
        try:
            target = date.fromisoformat(a.date_s)
        except ValueError:
            p.error(f"--date deve essere in formato YYYY-MM-DD, ricevuto: {a.date_s!r}")
    return a.period, target, a.do_all


def main(argv: list[str] | None = None) -> int:
    period, target, do_all = parse_args(argv if argv is not None else sys.argv[1:])
    all_notes = load_all_notes()
    if not all_notes:
        print("Nessuna nota trovata.")
        return 0

    if do_all:
        targets = all_periods(period, all_notes)
        for t in targets:
            out = generate_one(period, t, all_notes)
            print(f"  scritto: {out.relative_to(WIKI).as_posix()}")
        print(f"Digest {period}: rigenerati {len(targets)} file.")
    else:
        t = target or date.today()
        out = generate_one(period, t, all_notes)
        print(f"Digest {period} per {t}: {out.relative_to(WIKI).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
