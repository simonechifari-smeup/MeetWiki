"""
MeetWiki ingest — converte file .md grezzi da note_riunioni/
in note strutturate in MeetWiki/notes/ con frontmatter YAML.

Conforme alla skill .github/skills/meetwiki-ingest/SKILL.md.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "note_riunioni"
WIKI_DIR = ROOT / "MeetWiki"
NOTES_DIR = WIKI_DIR / "notes"
HISTORY_DIR = NOTES_DIR / "_history"
MANIFEST = WIKI_DIR / ".meta" / "manifest.json"

FILENAME_DATE_RE = re.compile(r"(\d{4})_(\d{2})_(\d{2})")
FILENAME_TIME_RE = re.compile(r"\d{4}_\d{2}_\d{2}\s+(\d{2})_(\d{2})")
LANG_SUFFIX_RE = re.compile(r"\s*\((Italian|English)\)\s*(?=\.md$)", re.IGNORECASE)
TIMESTAMP_RE = re.compile(r"(\d{4}_\d{2}_\d{2})\s+(\d{2}_\d{2})\s+\w+")
EMAIL_PERSON_RE = re.compile(r"\[([^\]]+)\]\(mailto:([^)]+)\)")
GOOGLE_DOC_RE = re.compile(r"https?://docs\.google\.com/document/d/[\w-]+")
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
BULLET_BOLD_RE = re.compile(r"^\*\s+\*\*([^*]+)\*\*", re.MULTILINE)
ACTION_RE = re.compile(r"^- \[ \]\s+\\?\[?([^\]\\]+?)\\?\]?\s+(.+?)$", re.MULTILINE)

KEYWORD_TAGS = {
    # multi-word PRIMA delle single-word (ordine importa per il match)
    "patch management": "patch-management",
    "data center": "data-center",
    "datacenter": "data-center",
    "nuove leve": "nuove-leve",
    "meet settimanale": "data-center",
    "meet di allineamento": "allineamento",
    "fasatura": "fasatura",
    "kickoff": "kickoff",
    "fortinet": "fortinet",
    "firewall": "firewall",
    "monitoraggio": "monitoraggio",
    "report": "report",
    "unipol": "unipol",
    "pel": "pel",
    "gov": "gov",
    "ansible": "ansible",
    "acronis": "acronis",
    "rubrica": "rubrica",
    "migrazione": "migrazione",
    "dev ai": "dev-ai",
    "tool": "tool",
}

# Caratteri considerati "parola" per il match dei keyword.
# Trattino e underscore sono separatori (cosi 'team' non matcha 'teamacronis'
# ma matcha 'team_acronis' o 'team-acronis').
_KW_BOUNDARY = re.compile(r"[a-z0-9]")


def _kw_match(keyword: str, text: str) -> bool:
    """Match con confini di parola: il keyword non deve essere preceduto/seguito
    da [a-z0-9] (lettere o cifre). Spazi, trattini, underscore e punteggiatura ok."""
    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _dedup_key(name: str) -> tuple[str, str]:
    """Chiave di dedup: (timestamp_meeting, nome_senza_lang_suffix).
    Varianti EN/IT dello stesso meeting hanno stesso timestamp e stesso base."""
    ts_m = TIMESTAMP_RE.search(name)
    ts = f"{ts_m.group(1)} {ts_m.group(2)}" if ts_m else name
    base = LANG_SUFFIX_RE.sub("", name)
    return ts, base


def _lang_priority(name: str) -> int:
    """Priorita per scegliere la variante canonica: italian < no-lang < english."""
    lm = LANG_SUFFIX_RE.search(name)
    if not lm:
        return 1
    return 0 if lm.group(1).lower() == "italian" else 2


def select_canonical(files: list[Path]) -> tuple[list[Path], dict[Path, Path]]:
    """Raggruppa per timestamp+base e tiene una sola variante per gruppo.
    Restituisce (file_canonici, mappa_duplicati path->path_canonico)."""
    groups: dict[tuple[str, str], list[Path]] = {}
    for f in files:
        groups.setdefault(_dedup_key(f.name), []).append(f)
    canonical: list[Path] = []
    dup_map: dict[Path, Path] = {}
    for group in groups.values():
        if len(group) == 1:
            canonical.append(group[0])
            continue
        chosen = min(group, key=lambda f: (_lang_priority(f.name), f.name))
        canonical.append(chosen)
        for f in group:
            if f is not chosen:
                dup_map[f] = chosen
    return canonical, dup_map


def _archive_source(src: Path, meeting_date: str) -> Path:
    """Sposta `src` in note_riunioni/archive/YYYY-MM/ se non gia' li'.
    Restituisce il path finale (post-move se avvenuto, src altrimenti)."""
    archive_dir = SOURCE_DIR / "archive" / meeting_date[:7]
    if src.parent == archive_dir:
        return src
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / src.name
    if dest.exists():
        # Collisione: stesso nome gia' archiviato. Tieni il piu' recente.
        dest.unlink()
    src.rename(dest)
    return dest


def slugify(text: str, maxlen: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:maxlen].rstrip("-")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_filename(name: str) -> tuple[str, str, str]:
    """Restituisce (meeting_date YYYY-MM-DD, title, lang_suffix)."""
    stem = name[:-3] if name.endswith(".md") else name
    # Data riunione dal timestamp embedded
    m = FILENAME_DATE_RE.search(stem)
    if m:
        meeting_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    else:
        meeting_date = stem[:10] if re.match(r"\d{4}-\d{2}-\d{2}", stem) else \
            datetime.now().strftime("%Y-%m-%d")

    # Rimuovi prefisso "YYYY-MM-DD - "
    rest = re.sub(r"^\d{4}-\d{2}-\d{2}\s*-\s*", "", stem)
    # Rimuovi suffisso " - <timestamp> ... - Appunti di Gemini" o varianti
    rest = re.sub(
        r"\s*-\s*\d{4}_\d{2}_\d{2}\s+\d{2}_\d{2}\s+\w+\s*-\s*"
        r"(Appunti di Gemini|Notes by Gemini)(\s*\([^)]+\))?\s*$",
        "", rest, flags=re.IGNORECASE
    )
    # Lang suffix se presente (Italian/English)
    lang_match = re.search(r"\((Italian|English)\)", name, re.IGNORECASE)
    lang = lang_match.group(1).lower() if lang_match else ""

    title = rest.strip().replace("_", ":")
    return meeting_date, title, lang


def extract_participants(text: str) -> list[str]:
    """Cerca pattern [Nome](mailto:...) nelle prime 30 righe."""
    head = "\n".join(text.splitlines()[:30])
    people: list[str] = []
    seen: set[str] = set()
    for m in EMAIL_PERSON_RE.finditer(head):
        name = m.group(1).strip()
        # Skip mailing list / generic
        if "@" in name or name.lower().startswith(("ics ", "team ", "lista")):
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            people.append(name)
    return people


def extract_section(text: str, heading: str) -> str:
    """Estrae il contenuto della sezione `### heading` fino al prossimo `### `."""
    pattern = re.compile(
        rf"^###\s+{re.escape(heading)}\s*\n(.*?)(?=^###\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def extract_action_items(text: str) -> list[str]:
    """Linee `- [ ] [Persona] descrizione` dalla sezione Passaggi successivi."""
    section = extract_section(text, "Passaggi successivi") or \
              extract_section(text, "Next steps") or ""
    items: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("- [ ]"):
            continue
        # Pulisci escape backslash
        clean = line.replace("\\[", "[").replace("\\]", "]")
        items.append(clean)
    return items


def extract_topics(text: str) -> list[str]:
    """Titoli in grassetto dei bullet della sezione Dettagli."""
    section = extract_section(text, "Dettagli") or \
              extract_section(text, "Details") or ""
    return [m.strip().rstrip(":") for m in BULLET_BOLD_RE.findall(section)]


def extract_doc_links(text: str) -> list[str]:
    return sorted(set(GOOGLE_DOC_RE.findall(text)))


def auto_tags(title: str) -> list[str]:
    """Solo tag da whitelist curata, con match a confini di parola per
    evitare falsi positivi (es. 'team' dentro 'teamacronis')."""
    tags: set[str] = set()
    tlow = title.lower()
    for kw, tag in KEYWORD_TAGS.items():
        if _kw_match(kw, tlow):
            tags.add(tag)
    return sorted(tags)


def yaml_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "\n" + "\n".join(f"  - {json.dumps(v, ensure_ascii=False)}" for v in values)


def build_note(
    *, note_id: str, title: str, date: str, source_rel: str, source_hash: str,
    ingested_at: str, participants: list[str], tags: list[str],
    related_docs: list[str], summary: str, topics: list[str],
    actions: list[str], raw: str,
) -> str:
    fm_title = json.dumps(title, ensure_ascii=False)
    fm_src = json.dumps(source_rel, ensure_ascii=False)
    lines = [
        "---",
        f"id: {note_id}",
        f"title: {fm_title}",
        f"date: {date}",
        f"source: {fm_src}",
        f'source_hash: "sha256:{source_hash}"',
        f"ingested_at: {ingested_at}",
        f"participants:{yaml_list(participants)}",
        f"tags:{yaml_list(tags)}",
        f"related_docs:{yaml_list(related_docs)}",
        "---",
        "",
        "## Riepilogo",
        summary.strip() or "_Nessun riepilogo disponibile._",
        "",
        "## Partecipanti",
    ]
    if participants:
        lines.extend(f"- {p}" for p in participants)
    else:
        lines.append("_Nessun partecipante estratto._")
    lines += ["", "## Argomenti"]
    if topics:
        lines.extend(f"- {t}" for t in topics)
    else:
        lines.append("_Nessun argomento estratto._")
    lines += ["", "## Decisioni", "_Nessuna decisione esplicita estratta automaticamente._",
              "", "## Action Items"]
    if actions:
        lines.extend(actions)
    else:
        lines.append("_Nessuna azione tracciata._")
    lines += ["", "## Trascrizione / Note originali", "", raw.rstrip(), ""]
    return "\n".join(lines)


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"version": 1, "ingested": {}}


def save_manifest(data: dict) -> None:
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    force = "--force" in sys.argv
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    ingested_map: dict = manifest.setdefault("ingested", {})

    files = sorted(SOURCE_DIR.rglob("*.md"))
    print(f"Trovati {len(files)} file in {SOURCE_DIR.name}/ (inclusa archive/)"
          + (" (FORCE)" if force else ""))

    # Pre-pass 1: dedup varianti lingua (stesso timestamp+titolo)
    files, dup_map = select_canonical(files)
    for dup_path, target_path in dup_map.items():
        print(f"  [DUP-LANG] {dup_path.name} -> stesso meeting di {target_path.name}, salto")
        ingested_map[dup_path.name] = {
            "dup_of": target_path.name,
            "ingested_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        # Archivia anche il duplicato (stesso month del canonical)
        meeting_date, _, _ = parse_filename(target_path.name)
        _archive_source(dup_path, meeting_date)

    # Pre-pass 2: rileva collisioni di note_id (stesso date+slug ma timestamp diversi)
    base_ids: dict[str, list[str]] = {}
    for src in files:
        meeting_date, title, _ = parse_filename(src.name)
        base_id = f"{meeting_date}-{slugify(title)}"
        base_ids.setdefault(base_id, []).append(src.name)
    needs_time_suffix = {n for names in base_ids.values() if len(names) > 1 for n in names}

    new_count = updated_count = skipped_count = 0
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for src in files:
        digest = sha256_file(src)
        prev = ingested_map.get(src.name)
        if prev and prev.get("hash") == digest and not force:
            skipped_count += 1
            continue

        meeting_date, title, _lang = parse_filename(src.name)
        slug = slugify(title)
        if src.name in needs_time_suffix:
            tm = FILENAME_TIME_RE.search(src.name)
            if tm:
                slug = f"{slug}-{tm.group(1)}{tm.group(2)}"
        note_id = f"{meeting_date}-{slug}"[:80].rstrip("-")
        month_dir = NOTES_DIR / meeting_date[:7]  # YYYY-MM
        month_dir.mkdir(parents=True, exist_ok=True)
        out_path = month_dir / f"{note_id}.md"

        raw = src.read_text(encoding="utf-8", errors="replace")
        participants = extract_participants(raw)
        summary = extract_section(raw, "Riepilogo") or extract_section(raw, "Summary")
        # Pulizia footer "Valuta questo riepilogo:"
        summary = re.sub(r"\n+\*Valuta questo riepilogo:.*$", "", summary, flags=re.DOTALL).strip()
        topics = extract_topics(raw)
        actions = extract_action_items(raw)
        docs = extract_doc_links(raw)
        tags = auto_tags(title)

        # Backup precedente se differente
        if prev and out_path.exists():
            old_hash = prev.get("hash", "unknown")[:8]
            hist_dir = HISTORY_DIR / meeting_date[:7]
            hist_dir.mkdir(parents=True, exist_ok=True)
            archive = hist_dir / f"{note_id}-{old_hash}.md"
            archive.write_text(out_path.read_text(encoding="utf-8"), encoding="utf-8")

        content = build_note(
            note_id=note_id, title=title, date=meeting_date,
            source_rel=f"note_riunioni/{src.relative_to(SOURCE_DIR).as_posix()}",
            source_hash=digest, ingested_at=now_iso,
            participants=participants, tags=tags, related_docs=docs,
            summary=summary, topics=topics, actions=actions, raw=raw,
        )
        out_path.write_text(content, encoding="utf-8")

        if prev:
            updated_count += 1
            status = "AGGIORNATA"
        else:
            new_count += 1
            status = "NUOVA"
        print(f"  [{status}] {src.name} -> {out_path.name}")

        # Archivia il sorgente in note_riunioni/archive/YYYY-MM/ se non gia' li'
        archived = _archive_source(src, meeting_date)
        source_rel_final = f"note_riunioni/{archived.relative_to(SOURCE_DIR).as_posix()}"
        # Riscrivi la nota con il source path aggiornato (post-archive) se cambiato
        if archived != src:
            content = build_note(
                note_id=note_id, title=title, date=meeting_date,
                source_rel=source_rel_final, source_hash=digest, ingested_at=now_iso,
                participants=participants, tags=tags, related_docs=docs,
                summary=summary, topics=topics, actions=actions, raw=raw,
            )
            out_path.write_text(content, encoding="utf-8")

        ingested_map[src.name] = {
            "id": note_id,
            "path": str(out_path.relative_to(WIKI_DIR).as_posix()),
            "source": source_rel_final,
            "hash": digest,
            "ingested_at": now_iso,
        }

    save_manifest(manifest)
    print(
        f"\nIngest completato: {new_count} nuove, {updated_count} aggiornate, "
        f"{skipped_count} saltate (gia aggiornate)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
