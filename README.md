# Gemini Notes → MeetWiki

Pipeline che scarica le note di riunione generate da Gemini in Gmail e le organizza in una wiki strutturata, pronta per LLM e ricerca.

## Quick start

```powershell
# 1. Setup una tantum
scripts\setup.bat

# 2. Scarica nuove note da Gmail
run.bat

# 3. Aggiorna la wiki (ingest + index + summarize)
.venv\Scripts\python.exe scripts\meetwiki_update.py
```

## Struttura

```
.
├── run.bat                       # Entry-point download (task scheduler)
├── scripts/                      # Codice Python e script ausiliari
│   ├── gemini_notes_downloader.py
│   ├── meetwiki_*.py             # Pipeline wiki
│   ├── setup.bat
│   └── schedule_task.bat
├── MeetWiki/                     # Wiki strutturata (note ingerite)
├── note_riunioni/                # Inbox + archive sorgenti .md
├── .cache/                       # Stato runtime (dedup email)
├── .env                          # OUTPUT_DIR e config
└── requirements.txt
```

## Documentazione

- **[AGENTS.md](AGENTS.md)** — istruzioni per agenti AI e convenzioni del progetto
- **[MeetWiki/README.md](MeetWiki/README.md)** — struttura della wiki, setup Obsidian/Kanban e skill disponibili
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — guida rapida Copilot

### Obsidian (Kanban personale)

Il vault `MeetWiki/` include `.obsidian/` versionata + il plugin `obsidian-kanban`
bundled. Apri la cartella in Obsidian, abilita i community plugins una volta
(Restricted mode → Turn on) e gestisci i tuoi task in `MY-KANBAN.md`.
Vedi [MeetWiki/README.md](MeetWiki/README.md#obsidian-setup-e-uso) per il workflow completo.

## Stack

- Python 3.14 (in `.venv/`)
- Playwright 1.44 (Chrome con CDP su porta 9222)
- Zero dipendenze YAML (parser regex custom)
