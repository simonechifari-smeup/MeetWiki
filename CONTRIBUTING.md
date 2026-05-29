# Contributing

Grazie per l'interesse nel progetto MeetWiki. Linee guida sintetiche per contribuire.

## Setup

```powershell
git clone <repo>
cd GMAIL
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m playwright install chromium
```

In alternativa: `pip install -r requirements.txt` per le sole dipendenze runtime.

## Variabili d'ambiente

Copiare `.env.example` (se presente) in `.env`. Le principali:

- `MEETWIKI_OWNER` — owner principale del Kanban personale (default: persona piu' frequente)
- `GMAIL_USER`, `GMAIL_LABEL` — per il downloader Gemini

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

I test coprono le funzioni pure (parsing frontmatter, slugify, hashing action items,
tokenizzazione BM25, range settimana/mese). I test toccano solo `tests/` e usano
`tmp_path`: non scrivono mai dentro `MeetWiki/`.

## Linting / formattazione

```powershell
.\.venv\Scripts\python.exe -m ruff check scripts tests
.\.venv\Scripts\python.exe -m ruff format scripts tests
```

Configurazione in `pyproject.toml`. `line-length=100`, target Python 3.11.

## Pipeline locale (smoke test)

Dopo modifiche significative agli script `meetwiki_*`, eseguire la pipeline su
una copia dei dati o in dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\meetwiki_update.py --dry-run
```

Per un giro completo:

```powershell
.\.venv\Scripts\python.exe scripts\meetwiki_update.py --skip-search --skip-kanban
```

## Convenzioni di codice

- Niente dipendenze YAML: il parser regex e' intenzionale (vedi `scripts/meetwiki_common.py`).
- Niente comandi git tramite MCP GitKraken/GitLens: usare il binario `git` direttamente.
- Tag in `kebab-case`, whitelist curata in `KEYWORD_TAGS` (`scripts/meetwiki_ingest.py`).
- I file generati portano `generated_at` nel frontmatter e sono sicuri da rigenerare.
- Vedi [AGENTS.md](AGENTS.md) per le invarianti complete del progetto.

## PR checklist

- [ ] `pytest` passa
- [ ] `ruff check` passa
- [ ] Pipeline `meetwiki_update.py --dry-run` non solleva errori
- [ ] Documentazione aggiornata (README, AGENTS.md, skill `.github/skills/` se rilevante)
- [ ] Voce in `CHANGELOG.md` sotto `## [Unreleased]`
