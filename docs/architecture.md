# 🏗️ Architettura

## Diagramma di flusso

```
┌─────────────┐     ┌─────────────────────────┐     ┌─────────────────────┐
│    Gmail    │────>│ gemini_notes_downloader │────>│  note_riunioni/     │
│  (Gemini)   │     │  (Playwright + CDP)     │     │  (inbox .md files)  │
└─────────────┘     └─────────────────────────┘     └─────────┬───────────┘
                                                              │
                                                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       meetwiki_update.py                               │
│                                                                        │
│   ┌─────────┐  ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐   │
│   │ ingest  │─>│  index  │─>│ summarize │─>│ actions │─>│  digest  │   │
│   └─────────┘  └─────────┘  └───────────┘  └─────────┘  └──────────┘   │
│        │                                         │              │      │
│        ▼                                         ▼              ▼      │
│   ┌──────────┐                             ┌──────────┐  ┌──────────┐  │
│   │  kanban  │<─── sync bidirezionale ────>│ Obsidian │  │  search  │  │
│   └──────────┘                             └──────────┘  └──────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MeetWiki/                                                             │
│  ├── notes/YYYY-MM/        ← note strutturate con frontmatter          │
│  ├── topics/               ← pagine aggregate per argomento            │
│  ├── people/               ← profili per partecipante                  │
│  ├── actions/              ← tracker + kanban board                    │
│  ├── digests/              ← sintesi settimanali/mensili               │
│  └── .meta/                ← manifest, search index, status            │
└────────────────────────────────────────────────────────────────────────┘
```

## Componenti principali

### Download (`gemini_notes_downloader.py`)
- Connessione a Chrome via CDP (porta 9222) con profilo utente persistente
- Cerca email Gemini in Gmail, estrae link Google Docs
- Esporta i documenti in Markdown e li salva in `note_riunioni/`
- Deduplicazione via `.cache/processed_emails.json`

### Ingest (`meetwiki_ingest.py`)
- Legge i file `.md` dalla inbox
- Estrae: data, titolo, partecipanti, tag (da whitelist `KEYWORD_TAGS`)
- Genera frontmatter YAML e sezioni canoniche
- Dedup SHA-256 in `.meta/manifest.json`
- Gestione varianti EN/IT: priorità italiano
- Archivia sorgenti in `note_riunioni/archive/YYYY-MM/`

### Index (`meetwiki_index.py`)
- Rigenera `INDEX.md` (cronologico), `TAGS.md` (per tag), `PEOPLE.md` (per persona)
- Parser frontmatter custom via regex (zero dipendenze YAML)

### Summarize (`meetwiki_summarize.py`)
- Genera pagine `topics/{tag}.md` e `people/{persona}.md`
- Aggrega informazioni da tutte le note che condividono un tag/partecipante

### Actions (`meetwiki_actions.py`)
- Estrae action items da tutte le note
- Genera `ACTIONS.md` (vista globale) e `actions/by-owner/{slug}.md`
- Rispetta override manuali in `.meta/actions_status.json`

### Kanban (`meetwiki_kanban.py`)
- Sync bidirezionale con Obsidian (`--sync` legge board → aggiorna status)
- Export board (`--export` genera `.md` in formato obsidian-kanban)
- Colonne: `Open` | `In Progress` | `Blocked` | `Done`

### Search (`meetwiki_ask.py`)
- Indicizzazione BM25 in `.meta/search_index.json`
- Query in linguaggio naturale con filtri per tag/data
- Retrieval RAG-style con citazioni

### Common (`meetwiki_common.py`)
- Utility condivise da tutti gli script: `parse_frontmatter`, `extract_section`, `slugify`, `atomic_write_text`, `atomic_write_json`, `safe_load_json`, `validate_note_frontmatter`
- Scritture atomiche (`.tmp` + `os.replace`) per evitare file corrotti se la pipeline si interrompe

### Test e packaging
- Suite `pytest` in `tests/` (`test_pure_functions.py`, `test_integration.py`) sulle funzioni pure e su un end-to-end di ingest in `tmp_path`
- `pyproject.toml` centralizza dipendenze (`[project]`, extras `[project.optional-dependencies] dev`) e configurazione di `ruff` e `pytest`

## Scelte progettuali

| Scelta                   | Motivazione                                                     |
| ------------------------ | --------------------------------------------------------------- |
| Zero dipendenze YAML     | Portabilità, nessun `pip install pyyaml` necessario             |
| Parser regex custom      | Frontmatter semplice e controllato, nessuna complessità inutile |
| Playwright + CDP         | Chrome già loggato, nessuna configurazione OAuth                |
| SHA-256 per dedup        | Riconoscimento preciso di contenuti duplicati/aggiornati        |
| Link relativi            | Compatibilità Obsidian + GitHub rendering + portabilità         |
| Tag da whitelist         | Consistenza e pulizia della tassonomia                          |
| Partizionamento per mese | Scalabilità: evita cartelle con centinaia di file               |

> Lo schema esatto del frontmatter (campi obbligatori + limiti del parser) e' in
> [../MeetWiki/.meta/schema.md](../MeetWiki/.meta/schema.md).
