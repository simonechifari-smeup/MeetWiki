"""
MeetWiki ask — ricerca semantica + retrieval di passaggi (RAG) sulle note.

Indice BM25 puro Python (nessuna dipendenza esterna). Costruisce un indice
persistente in MeetWiki/.meta/search_index.json e lo usa per recuperare i
chunk piu' rilevanti rispetto a una query in linguaggio naturale.

Uso:
    python scripts/meetwiki_ask.py --index               # (re)build dell'indice
    python scripts/meetwiki_ask.py "decisioni su acronis"
    python scripts/meetwiki_ask.py -k 8 "trasferta faenza"
    python scripts/meetwiki_ask.py --tag data-center "patch management"
    python scripts/meetwiki_ask.py --since 2026-05-01 "kickoff dev ai"

L'output e' pensato per essere copiato in un prompt LLM: ogni chunk e'
citato con [titolo nota - data] e link relativo.

Conforme alla skill .github/skills/meetwiki-ask/SKILL.md.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "MeetWiki"
NOTES = WIKI / "notes"
INDEX_FILE = WIKI / ".meta" / "search_index.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meetwiki_common import (  # noqa: E402, I001
    atomic_write_json,
    parse_frontmatter,
    safe_load_json,
    validate_note_frontmatter,
)

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
TOKEN_RE = re.compile(r"[a-z0-9àèéìòù]{2,}")

# Stopwords italiano + inglese (minime, sufficienti per BM25)
STOPWORDS = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "del", "della",
    "dei", "delle", "degli", "dal", "dalla", "dai", "dalle", "dallo", "in", "nel",
    "nella", "nei", "nelle", "nello", "su", "sul", "sulla", "sui", "sulle", "sullo",
    "con", "per", "tra", "fra", "a", "ad", "da", "e", "ed", "o", "od", "ma", "se",
    "che", "chi", "cui", "non", "ne", "ci", "si", "te", "me", "tu", "io", "noi",
    "voi", "loro", "lei", "lui", "questo", "questa", "questi", "queste", "quel",
    "quello", "quella", "quelli", "quelle", "essere", "sono", "siamo", "siete",
    "sia", "stato", "stata", "era", "erano", "avere", "hanno", "abbiamo", "avete",
    "ho", "hai", "ha", "fare", "fa", "fai", "fanno", "come", "dove", "quando",
    "perche", "anche", "ancora", "gia", "piu", "meno", "molto", "poco", "tutto",
    "tutti", "tutte", "tutta", "stesso", "stessa", "ogni", "alcuni", "alcune",
    "the", "an", "of", "to", "on", "for", "with", "and", "or", "but",
    "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
    "do", "does", "did", "this", "that", "these", "those", "it", "its",
}

K1 = 1.5
B = 0.75
CHUNK_TARGET = 480     # caratteri target per chunk
CHUNK_MAX = 700        # taglio duro


def tokenize(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text)
    t = t.encode("ascii", "ignore").decode("ascii")  # rimuove accenti per matching robusto
    t = t.lower()
    return [w for w in TOKEN_RE.findall(t) if w not in STOPWORDS and len(w) > 1]


def split_sections(body: str) -> list[tuple[str, str]]:
    """Restituisce [(heading, content), ...] solo per sezioni canoniche.
    Esclude la trascrizione raw (rumore alto)."""
    allowed = {"Riepilogo", "Partecipanti", "Argomenti", "Decisioni", "Action Items"}
    parts: list[tuple[str, str]] = []
    matches = list(SECTION_RE.finditer(body))
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        if heading not in allowed:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        if not content:
            continue
        parts.append((heading, content))
    return parts


def chunk_text(text: str) -> list[str]:
    """Spezza il testo in chunk ~CHUNK_TARGET char, preferendo confini di paragrafo."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        if len(p) > CHUNK_MAX:
            # spezza per frase
            sentences = re.split(r"(?<=[.!?])\s+", p)
            for s in sentences:
                if len(buf) + len(s) + 1 > CHUNK_TARGET and buf:
                    chunks.append(buf.strip())
                    buf = ""
                buf = (buf + " " + s).strip() if buf else s
            continue
        if len(buf) + len(p) + 2 > CHUNK_TARGET and buf:
            chunks.append(buf.strip())
            buf = p
        else:
            buf = (buf + "\n\n" + p) if buf else p
    if buf.strip():
        chunks.append(buf.strip())
    # taglio duro di sicurezza
    out = []
    for c in chunks:
        if len(c) <= CHUNK_MAX:
            out.append(c)
        else:
            for i in range(0, len(c), CHUNK_MAX):
                out.append(c[i:i + CHUNK_MAX])
    return out


def build_index() -> dict:
    docs: list[dict] = []
    df: Counter = Counter()
    for p in sorted(NOTES.rglob("*.md")):
        if any(part.startswith("_") for part in p.relative_to(NOTES).parts):
            continue
        fm, body = parse_frontmatter(p.read_text(encoding="utf-8"))
        errs = validate_note_frontmatter(fm)
        if errs:
            print(f"WARN: {p.name}: {'; '.join(errs)}", file=sys.stderr)
            continue
        rel = p.relative_to(WIKI).as_posix()
        # chunk 0: titolo + tags + partecipanti (boost di matching)
        meta_chunk = f"{fm.get('title','')}\n" \
                     f"Tag: {', '.join(fm.get('tags') or [])}\n" \
                     f"Partecipanti: {', '.join(fm.get('participants') or [])}"
        sections = [("Metadati", meta_chunk)] + split_sections(body)
        for sec, content in sections:
            for ck in chunk_text(content):
                toks = tokenize(ck)
                if not toks:
                    continue
                tf = Counter(toks)
                docs.append({
                    "note_id": fm["id"],
                    "title": fm.get("title", fm["id"]),
                    "date": fm.get("date", ""),
                    "tags": fm.get("tags") or [],
                    "participants": fm.get("participants") or [],
                    "path": rel,
                    "section": sec,
                    "text": ck,
                    "tf": dict(tf),
                    "len": sum(tf.values()),
                })
                for term in tf:
                    df[term] += 1

    n_docs = len(docs)
    avgdl = sum(d["len"] for d in docs) / n_docs if n_docs else 0
    return {
        "version": 1,
        "built_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "n_docs": n_docs,
        "avgdl": avgdl,
        "df": dict(df),
        "docs": docs,
    }


def save_index(idx: dict) -> None:
    atomic_write_json(INDEX_FILE, idx, indent=None)


def load_index() -> dict | None:
    if not INDEX_FILE.exists():
        return None
    return safe_load_json(INDEX_FILE, None)


def bm25_score(query_terms: list[str], doc: dict, df: dict,
               n_docs: int, avgdl: float) -> float:
    score = 0.0
    dl = doc["len"]
    tf = doc["tf"]
    for q in query_terms:
        n_q = df.get(q, 0)
        if n_q == 0:
            continue
        idf = math.log(1 + (n_docs - n_q + 0.5) / (n_q + 0.5))
        f = tf.get(q, 0)
        if f == 0:
            continue
        denom = f + K1 * (1 - B + B * dl / avgdl) if avgdl else f
        score += idf * f * (K1 + 1) / denom
    return score


def search(idx: dict, query: str, k: int = 5,
           tag: str | None = None, since: str | None = None,
           until: str | None = None, person: str | None = None) -> list[dict]:
    q_terms = tokenize(query)
    if not q_terms:
        return []
    df = idx["df"]
    n = idx["n_docs"]
    avg = idx["avgdl"]
    scored = []
    person_low = person.lower() if person else None
    for d in idx["docs"]:
        if tag and tag not in (d.get("tags") or []):
            continue
        if since and d.get("date", "") < since:
            continue
        if until and d.get("date", "") > until:
            continue
        if person_low:
            if not any(person_low in p.lower() for p in (d.get("participants") or [])):
                continue
        s = bm25_score(q_terms, d, df, n, avg)
        if s > 0:
            scored.append((s, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": s, **d} for s, d in scored[:k]]


def render_results(query: str, results: list[dict]) -> str:
    if not results:
        return f"Nessun risultato per: {query!r}\n"
    out = [f"# Risultati per: {query!r}", "",
           f"Top {len(results)} chunk per rilevanza (BM25).", ""]
    for i, r in enumerate(results, 1):
        out.append(f"## {i}. [{r['date']}] {r['title']} — _{r['section']}_  "
                   f"(score {r['score']:.2f})")
        out.append(f"`{r['path']}`")
        out.append("")
        out.append("> " + r["text"].replace("\n", "\n> "))
        out.append("")
    return "\n".join(out)


def parse_args(argv: list[str]) -> dict:
    p = argparse.ArgumentParser(
        prog="meetwiki-ask",
        description="Ricerca BM25 + retrieval di passaggi sulle note MeetWiki.",
    )
    p.add_argument("--index", dest="do_index", action="store_true",
                   help="(re)build dell'indice BM25")
    p.add_argument("-k", "--top", type=int, default=5,
                   help="numero di passaggi da restituire (default: 5)")
    p.add_argument("--tag", default=None, help="filtra per tag")
    p.add_argument("--since", default=None, help="data minima YYYY-MM-DD")
    p.add_argument("--until", default=None, help="data massima YYYY-MM-DD")
    p.add_argument("--person", default=None, help="filtra per partecipante")
    p.add_argument("query", nargs="*", help="query in linguaggio naturale")
    a = p.parse_args(argv)
    return {
        "action": "index" if a.do_index else "search",
        "k": a.top,
        "tag": a.tag,
        "since": a.since,
        "until": a.until,
        "person": a.person,
        "query": " ".join(a.query).strip(),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args["action"] == "index":
        idx = build_index()
        save_index(idx)
        print(f"Indice costruito: {idx['n_docs']} chunk, "
              f"{len(idx['df'])} termini unici, "
              f"avg doc length {idx['avgdl']:.1f}. -> {INDEX_FILE.relative_to(WIKI).as_posix()}")
        return 0

    if not args["query"]:
        print("Uso: meetwiki_ask.py [opzioni] \"<query>\"\n"
              "     meetwiki_ask.py --index\n"
              "Opzioni: -k N | --tag T | --since YYYY-MM-DD | --until YYYY-MM-DD | --person Nome",
              file=sys.stderr)
        return 2

    idx = load_index()
    if idx is None:
        print("Indice non trovato. Lo costruisco ora...")
        idx = build_index()
        save_index(idx)

    results = search(idx, args["query"], k=args["k"], tag=args["tag"],
                     since=args["since"], until=args["until"], person=args["person"])
    print(render_results(args["query"], results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
