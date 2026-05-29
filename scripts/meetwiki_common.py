"""Utility condivise tra gli script meetwiki_*.

Pubbliche:
- atomic_write_json(path, data): write atomica via file temporaneo + replace (F04).
- safe_load_json(path, default, logger): load con rename-on-corrupt (F08).
- parse_frontmatter(text) -> (dict, body): parser YAML-like minimale (F09).
- extract_section(body, heading, level=2): estrae sezione markdown (F09).
- slugify(text, maxlen=None, fallback=""): slug ASCII kebab-case (F09).
"""
from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any, *, indent: int | None = 2) -> None:
    """Scrive JSON in modo atomico: write su file .tmp + os.replace.

    Garantisce che `path` non sia mai parzialmente scritto, anche su Ctrl+C
    o crash a meta' write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def safe_load_json(
    path: Path,
    default: Any,
    *,
    logger: logging.Logger | None = None,
) -> Any:
    """Load JSON con recupero esplicito su corruzione.

    Se il file non esiste -> ritorna `default`.
    Se il file e' corrotto -> lo rinomina in `<name>.corrupt.<timestamp>` e
    ritorna `default`, loggando ERROR. Cosi' l'utente vede il problema invece
    di perdere silenziosamente lo stato (F08).
    """
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_suffix(path.suffix + f".corrupt.{ts}")
        try:
            path.rename(backup)
        except OSError:
            backup = None
        msg = (
            f"[meetwiki] JSON corrotto in {path.name}: {exc}. "
            f"Rinominato in {backup.name if backup else '<rename failed>'}. "
            f"Ripartito da stato vuoto."
        )
        if logger is not None:
            logger.error(msg)
        else:
            print(msg)
        return default


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parser minimale YAML-like per frontmatter MeetWiki.

    Gestisce: `key: value` su singola riga, `key:` seguito da `  - item` (liste),
    `key: []` (lista vuota). NON gestisce escaping, multi-line, commenti inline,
    quote singole. Limiti documentati in `MeetWiki/.meta/schema.md`.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict = {}
    list_key: str | None = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and list_key:
            fm.setdefault(list_key, []).append(line[4:].strip().strip('"'))
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if v == "":
                fm[k] = []
                list_key = k
            elif v == "[]":
                fm[k] = []
                list_key = None
            else:
                fm[k] = v.strip('"')
                list_key = None
    return fm, m.group(2)


def extract_section(body: str, heading: str, *, level: int = 2) -> str:
    """Estrae il contenuto di una sezione markdown di livello `level` (default 2).

    Per ingest si usa `level=3` (sezioni Gemini), per le note canoniche `level=2`.
    """
    hashes = "#" * level
    pat = re.compile(
        rf"^{hashes}\s+{re.escape(heading)}\s*\n(.*?)(?=^{hashes}\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(body)
    return m.group(1).strip() if m else ""


def slugify(text: str, *, maxlen: int | None = None, fallback: str = "") -> str:
    """Slug ASCII kebab-case. Se vuoto, ritorna `fallback`."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if maxlen is not None:
        text = text[:maxlen].rstrip("-")
    return text or fallback
