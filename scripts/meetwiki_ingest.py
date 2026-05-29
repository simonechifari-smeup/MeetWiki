"""
MeetWiki ingest — converte file .md grezzi da note_riunioni/
in note strutturate in MeetWiki/notes/ con frontmatter YAML.

Conforme alla skill .github/skills/meetwiki-ingest/SKILL.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "note_riunioni"
WIKI_DIR = ROOT / "MeetWiki"
NOTES_DIR = WIKI_DIR / "notes"
HISTORY_DIR = NOTES_DIR / "_history"
MANIFEST = WIKI_DIR / ".meta" / "manifest.json"

log = logging.getLogger("meetwiki.ingest")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meetwiki_common import (  # noqa: E402, I001
    atomic_write_json,
    atomic_write_text,
    extract_section as _common_extract_section,
    safe_load_json,
    slugify as _common_slugify,
)

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

    In caso di collisione di nome:
    - se il file gia' archiviato ha lo stesso hash -> scarta `src` (identici).
    - altrimenti rinomina `src` con suffisso `-2`, `-3`, ... (F07).
    Restituisce il path finale (post-move se avvenuto, src altrimenti).
    """
    archive_dir = SOURCE_DIR / "archive" / meeting_date[:7]
    if src.parent == archive_dir:
        return src
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / src.name
    if dest.exists():
        if sha256_file(dest) == sha256_file(src):
            # Identici: scarta il duplicato in inbox.
            src.unlink()
            return dest
        # Contenuti diversi: salva con suffisso numerico, non sovrascrivere.
        n = 2
        while True:
            candidate = dest.with_stem(f"{dest.stem}-{n}")
            if not candidate.exists():
                dest = candidate
                break
            n += 1
        print(f"  [ARCHIVE-COLLISION] {src.name} differisce da quello gia' archiviato, salvo come {dest.name}")
    src.rename(dest)
    return dest


def slugify(text: str, maxlen: int = 60) -> str:
    return _common_slugify(text, maxlen=maxlen)



def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_filename(name: str) -> tuple[str | None, str, str]:
    """Restituisce (meeting_date YYYY-MM-DD | None, title, lang_suffix).

    `meeting_date` e' None se il filename non contiene un timestamp riconoscibile:
    in quel caso il caller deve loggare un warning e saltare il file (F06).
    """
    stem = name[:-3] if name.endswith(".md") else name
    # Data riunione dal timestamp embedded
    m = FILENAME_DATE_RE.search(stem)
    if m:
        meeting_date: str | None = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    elif re.match(r"\d{4}-\d{2}-\d{2}", stem):
        meeting_date = stem[:10]
    else:
        meeting_date = None

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
            log.debug("Skip partecipante non-persona: %r", name)
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            people.append(name)
    return people


def extract_section(text: str, heading: str) -> str:
    """Estrae il contenuto della sezione `### heading` fino al prossimo `### `."""
    return _common_extract_section(text, heading, level=3)



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
    return safe_load_json(MANIFEST, {"version": 1, "ingested": {}})


def save_manifest(data: dict) -> None:
    atomic_write_json(MANIFEST, data)


def main() -> int:
    p = argparse.ArgumentParser(
        prog="meetwiki-ingest",
        description="Importa file .md da note_riunioni/ nella wiki strutturata MeetWiki/notes/.",
    )
    p.add_argument("--force", action="store_true",
                   help="re-ingest di tutti i file, ignorando hash in manifest")
    p.add_argument("--dry-run", action="store_true",
                   help="mostra cosa verrebbe ingerito/archiviato senza scrivere nulla")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="abilita log DEBUG (es. partecipanti scartati)")
    args = p.parse_args()
    force = args.force
    dry_run = args.dry_run

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    prefix = "[DRY-RUN] " if dry_run else ""
    if not dry_run:
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    ingested_map: dict = manifest.setdefault("ingested", {})

    files = sorted(SOURCE_DIR.rglob("*.md"))
    print(f"{prefix}Trovati {len(files)} file in {SOURCE_DIR.name}/ (inclusa archive/)"
          + (" (FORCE)" if force else ""))

    # Pre-pass 1: dedup varianti lingua (stesso timestamp+titolo)
    files, dup_map = select_canonical(files)
    for dup_path, target_path in dup_map.items():
        print(f"  {prefix}[DUP-LANG] {dup_path.name} -> stesso meeting di {target_path.name}, salto")
        ingested_map[dup_path.name] = {
            "dup_of": target_path.name,
            "ingested_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        # Archivia anche il duplicato (stesso month del canonical)
        meeting_date, _, _ = parse_filename(target_path.name)
        if meeting_date is None:
            print(f"  [SKIP] {target_path.name}: filename senza data riconoscibile (YYYY_MM_DD o YYYY-MM-DD)")
            continue
        if not dry_run:
            _archive_source(dup_path, meeting_date)

    # Pre-pass 2: rileva collisioni di note_id (stesso date+slug ma timestamp diversi)
    base_ids: dict[str, list[str]] = {}
    skipped_undated: list[str] = []
    valid_files: list[Path] = []
    for src in files:
        meeting_date, title, _ = parse_filename(src.name)
        if meeting_date is None:
            skipped_undated.append(src.name)
            continue
        valid_files.append(src)
        base_id = f"{meeting_date}-{slugify(title)}"
        base_ids.setdefault(base_id, []).append(src.name)
    for n in skipped_undated:
        print(f"  [SKIP] {n}: filename senza data riconoscibile, ignorato (rinomina con prefisso YYYY-MM-DD o timestamp YYYY_MM_DD)")
    files = valid_files
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
        if not dry_run:
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

        # F28: rileva modifiche manuali alla nota canonica confrontando
        # l'hash attuale con quello dell'ultima nota generata dall'ingest.
        current_note_hash = (
            hashlib.sha256(out_path.read_bytes()).hexdigest() if out_path.exists() else None
        )
        last_generated = prev.get("generated_note_hash") if prev else None
        if (
            not dry_run
            and current_note_hash
            and last_generated
            and current_note_hash != last_generated
        ):
            content_preview = build_note(
                note_id=note_id, title=title, date=meeting_date,
                source_rel=f"note_riunioni/{src.relative_to(SOURCE_DIR).as_posix()}",
                source_hash=digest, ingested_at=now_iso,
                participants=participants, tags=tags, related_docs=docs,
                summary=summary, topics=topics, actions=actions, raw=raw,
            )
            conflict_path = out_path.with_suffix(".conflict.md")
            atomic_write_text(conflict_path, content_preview)
            print(
                f"  [CONFLICT] {out_path.name}: modifiche manuali rilevate, "
                f"scritto {conflict_path.name} (manifest non aggiornato)."
            )
            skipped_count += 1
            continue

        # Backup precedente se differente
        if prev and out_path.exists():
            old_hash = prev.get("hash", "unknown")[:8]
            hist_dir = HISTORY_DIR / meeting_date[:7]
            if not dry_run:
                hist_dir.mkdir(parents=True, exist_ok=True)
                archive = hist_dir / f"{note_id}-{old_hash}.md"
                atomic_write_text(archive, out_path.read_text(encoding="utf-8"))

        content = build_note(
            note_id=note_id, title=title, date=meeting_date,
            source_rel=f"note_riunioni/{src.relative_to(SOURCE_DIR).as_posix()}",
            source_hash=digest, ingested_at=now_iso,
            participants=participants, tags=tags, related_docs=docs,
            summary=summary, topics=topics, actions=actions, raw=raw,
        )
        if not dry_run:
            atomic_write_text(out_path, content)

        if prev:
            updated_count += 1
            status = "AGGIORNATA"
        else:
            new_count += 1
            status = "NUOVA"
        print(f"  {prefix}[{status}] {src.name} -> {out_path.name}")

        # Archivia il sorgente in note_riunioni/archive/YYYY-MM/ se non gia' li'
        if dry_run:
            archived = src
        else:
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
            if not dry_run:
                atomic_write_text(out_path, content)

        ingested_map[src.name] = {
            "id": note_id,
            "path": str(out_path.relative_to(WIKI_DIR).as_posix()),
            "source": source_rel_final,
            "hash": digest,
            "generated_note_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "ingested_at": now_iso,
        }

    if not dry_run:
        save_manifest(manifest)
    print(
        f"\n{prefix}Ingest completato: {new_count} nuove, {updated_count} aggiornate, "
        f"{skipped_count} saltate (gia aggiornate)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
