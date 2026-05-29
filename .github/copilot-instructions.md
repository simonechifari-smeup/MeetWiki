# Istruzioni progetto MeetWiki

Questo workspace contiene:
1. **`scripts/gemini_notes_downloader.py`** — automazione browser che scarica note Gemini da Gmail in `note_riunioni/`.
2. **`MeetWiki/`** — wiki strutturata per LLM con le note ingerite.
3. **`.github/skills/`** — skill per gestire la wiki.

## Skill MeetWiki disponibili

Quando l'utente lavora con la wiki dei meet, usa le skill in `.github/skills/`:

- **`meetwiki-update`** → pipeline completa: ingest + index + summarize + actions + digest + search index (preferita per "aggiorna la wiki")
- **`meetwiki-ingest`** → importa nuove note da `note_riunioni/` in `MeetWiki/notes/`
- **`meetwiki-index`** → rigenera `INDEX.md`, `TAGS.md`, `PEOPLE.md`
- **`meetwiki-summarize`** → genera pagine aggregate `topics/` e `people/`
- **`meetwiki-actions`** → aggrega action items in `ACTIONS.md` e `actions/by-owner/`
- **`meetwiki-digest`** → genera digest settimanali/mensili in `digests/`
- **`meetwiki-kanban`** → board Obsidian Kanban (`MY-KANBAN.md` + per-owner) con sync bidirezionale
- **`meetwiki-search`** → grep esatto sulle note (NON modifica)
- **`meetwiki-ask`** → ricerca BM25 + retrieval di passaggi per Q&A in linguaggio naturale
- **`project-review`** → esegue code review sistematica del progetto (correttezza, sicurezza, architettura, doc, test)
- **`docs-review`** → revisiona e integra inline la documentazione (README, AGENTS.md, docs/*.md, skill, CONTRIBUTING)

Leggi sempre il file `SKILL.md` della skill prima di operare.

## Flusso tipico

```
Gmail → scripts/gemini_notes_downloader.py → note_riunioni/*.md
                                          ↓
                                  meetwiki-update
                                  (ingest → index → summarize)
                                          ↓
                                  MeetWiki/{notes,topics,people}/*.md
                                          ↓
                                  Ricerca via meetwiki-search
```

Per step singoli usare le skill granulari (`meetwiki-ingest`, `meetwiki-index`, `meetwiki-summarize`).

## Convenzioni

- File note: `notes/YYYY-MM-DD-slug.md` con frontmatter YAML (schema in `MeetWiki/.meta/schema.md`)
- Tag in `kebab-case`
- Tutti i link interni alla wiki sono **relativi**
- File generati portano `generated_at` nel frontmatter — sicuri da rigenerare
