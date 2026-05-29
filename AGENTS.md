# AGENTS.md

Istruzioni operative per agenti AI che lavorano in questo workspace.
Leggere SEMPRE questo file all'inizio della sessione.

## Contesto progetto

Pipeline di knowledge management per le note di riunioni Gemini:

```
Gmail → scripts/gemini_notes_downloader.py → note_riunioni/        (inbox)
                                          ↓
                                  meetwiki-update           (skill)
                                          ↓
                          MeetWiki/{notes,topics,people}/   (wiki LLM-ready)
                                          ↓
                                  note_riunioni/archive/    (sorgenti archiviati per mese)
```

- **`scripts/gemini_notes_downloader.py`**: Playwright + CDP su Chrome (porta 9222, profilo persistente `chrome_profile/`). Scarica .md da Gmail in `note_riunioni/`. Stato dedup email in `.cache/processed_emails.json`.
- **`MeetWiki/`**: wiki strutturata, frontmatter YAML, link relativi, partizionata per mese del meeting.
- **`scripts/meetwiki_*.py`**: 7 script idempotenti + 1 wrapper (`ingest`, `index`, `summarize`, `actions`, `digest`, `ask`, `kanban`, `update`).
- **`.github/skills/meetwiki-*/SKILL.md`**: 9 skill registrate in `.github/copilot-instructions.md`.
- **`MeetWiki/.obsidian/`**: vault Obsidian versionato. `community-plugins.json` abilita `obsidian-kanban` e `dataview`; i file binari dei plugin sono bundled in `.obsidian/plugins/` (NON serve installarli da Obsidian).

## Stack tecnico

- Python 3.14 in `.venv/` → eseguibile: `.venv\Scripts\python.exe`
- Playwright 1.44
- Nessun YAML parser esterno: regex custom (vedi `parse_frontmatter` in `meetwiki_index.py` e `parse_note` in `meetwiki_summarize.py`).
- Dedup: SHA-256 dei sorgenti in `MeetWiki/.meta/manifest.json`.

## Skill MeetWiki

Preferire SEMPRE la skill orchestratrice quando possibile.

| Skill                | Quando                                                                |
| -------------------- | --------------------------------------------------------------------- |
| `meetwiki-update`    | **Default** per "aggiorna la wiki": ingest + index + summarize + actions + digest + search + kanban |
| `meetwiki-ingest`    | Solo importare nuove note (raro: di solito basta `update`)            |
| `meetwiki-index`     | Solo rigenerare `INDEX.md`, `TAGS.md`, `PEOPLE.md`                    |
| `meetwiki-summarize` | Solo rigenerare `topics/*.md` e `people/*.md`                         |
| `meetwiki-actions`   | Rigenera tracker `ACTIONS.md` + `actions/by-owner/*.md`               |
| `meetwiki-digest`    | Genera digest settimanali/mensili in `digests/`                       |
| `meetwiki-kanban`    | Board Obsidian Kanban + sync bidirezionale dello stato                |
| `meetwiki-search`    | Grep esatto sulle riunioni (NON modifica file)                        |
| `meetwiki-ask`       | Q&A BM25 (retrieval RAG-style con citazioni)                          |

Leggere `SKILL.md` della skill prima di eseguirla.

## Comandi rapidi

```powershell
# Pipeline completa (caso 99%)
.venv\Scripts\python.exe scripts\meetwiki_update.py

# Re-ingest forzato (es. dopo modifica KEYWORD_TAGS o template build_note)
.venv\Scripts\python.exe scripts\meetwiki_update.py --force

# Solo pulizia pagine aggregate stale
.venv\Scripts\python.exe scripts\meetwiki_update.py --clean

# Salta digest o ricostruzione indice ricerca (pipeline piu' veloce)
.venv\Scripts\python.exe scripts\meetwiki_update.py --skip-digest --skip-search

# Reset distruttivo (chiedere conferma all'utente)
.venv\Scripts\python.exe scripts\meetwiki_update.py --reset

# Q&A semantico (BM25)
.venv\Scripts\python.exe scripts\meetwiki_ask.py "decisioni su acronis"
.venv\Scripts\python.exe scripts\meetwiki_ask.py --tag data-center --since 2026-05-01 "patch management"

# Digest ad-hoc
.venv\Scripts\python.exe scripts\meetwiki_digest.py                       # settimana corrente
.venv\Scripts\python.exe scripts\meetwiki_digest.py --period month        # mese corrente
.venv\Scripts\python.exe scripts\meetwiki_digest.py --all                 # tutti i settimanali storici

# Action items
.venv\Scripts\python.exe scripts\meetwiki_actions.py
.venv\Scripts\python.exe scripts\meetwiki_actions.py --list   # elenca con hash

# Kanban Obsidian (default: sync + export, sicuro)
.venv\Scripts\python.exe scripts\meetwiki_kanban.py
.venv\Scripts\python.exe scripts\meetwiki_kanban.py --sync        # solo legge le board e aggiorna status
.venv\Scripts\python.exe scripts\meetwiki_kanban.py --export      # solo rigenera le board
```

## Convenzioni e invarianti

### File system
- `note_riunioni/` = **inbox**: solo file mai ingeriti. Tutto il resto va in `note_riunioni/archive/YYYY-MM/` (mese del meeting).
- `MeetWiki/notes/YYYY-MM/{id}.md` = note canoniche, partizionate per mese del meeting.
- `MeetWiki/notes/_history/YYYY-MM/{id}-{hash8}.md` = backup automatici quando una nota cambia.
- `MeetWiki/topics/`, `MeetWiki/people/`, `MeetWiki/digests/`, `MeetWiki/actions/by-owner/`, `MeetWiki/actions/kanban/`, `MeetWiki/ACTIONS.md`, `MeetWiki/MY-KANBAN.md` = generati, sicuri da cancellare e rigenerare.
- `MeetWiki/.meta/manifest.json` = registro `{filename: {id, path, source, hash, ingested_at}}`. Distruzione = re-ingest from scratch.
- `MeetWiki/.meta/search_index.json` = indice BM25 di `meetwiki-ask`. Rigenerabile.
- `MeetWiki/.meta/actions_status.json` = override stato action items (`{hash: {status, closed_at, note}}`). **MAI cancellato dalla pipeline**, anche con `--reset`. Editato a mano dall'utente.

### Tag e taxonomy
- Whitelist curata in `KEYWORD_TAGS` dentro `scripts/meetwiki_ingest.py`. NON aggiungere tag dinamici dal titolo.
- Match a confini di parola (`_kw_match`): keyword non matcha dentro un'altra parola (es. `team` non matcha `teamacronis`, ma matcha `team_acronis`).
- Tag in `kebab-case`. Unificare sinonimi nel dizionario (es. `"datacenter"` e `"meet settimanale"` → `data-center`).

### Note
- `id` = `{date}-{slug}[-HHMM se collisione]`, max 80 char.
- Frontmatter obbligatorio (schema in `MeetWiki/.meta/schema.md`).
- Data = quella del meeting reale (timestamp embedded nel filename), MAI quella del download.
- Varianti EN/IT dello stesso meeting (stesso timestamp) → tengo solo IT (priorita': italian > no-lang > english). Le scartate finiscono nel manifest come `dup_of`.

### Link
- Tutti relativi. Da `topics/` o `people/`: `../notes/YYYY-MM/file.md`. Da `INDEX.md`: `notes/YYYY-MM/file.md`.

## Cosa fare dopo modifiche al codice

| Modifica                                | Azione                                                       |
| --------------------------------------- | ------------------------------------------------------------ |
| `KEYWORD_TAGS` o `auto_tags()`          | `meetwiki_update.py --force` + aggiornare README se rilevante|
| Template `build_note()`                 | `meetwiki_update.py --force`                                 |
| Layout cartelle (`notes/`, `archive/`)  | Aggiornare README.md + AGENTS.md + skill rilevanti           |
| Nuovo script `scripts/meetwiki_X.py`    | Creare `.github/skills/meetwiki-X/SKILL.md` + registrarla in `.github/copilot-instructions.md` + tabella README |
| Nuova skill                             | Aggiungerla a README.md tabella skill + `copilot-instructions.md` + AGENTS.md |
| Cambiamenti al formato manifest         | Documentare in `MeetWiki/.meta/schema.md` se serve           |

## Cosa NON fare

- NON modificare file in `MeetWiki/topics/` o `MeetWiki/people/` a mano: vengono sovrascritti.
- NON spostare/rinominare file in `MeetWiki/notes/` senza aggiornare il manifest.
- NON cancellare il manifest senza `--reset` (rompe il tracking hash).
- NON aggiungere `pyyaml` o dipendenze YAML: il parser regex e' intenzionale.
- NON committare `.venv/`, `chrome_profile/`, `note_riunioni/archive/` se l'utente non chiede esplicitamente.
- NON suggerire ottimizzazioni non richieste (over-engineering). Cambiare solo cio' che e' chiesto.
- NON rimuovere o duplicare le ancore `^h{hash10}` nelle board Kanban: rompi il sync bidirezionale.
- NON eseguire `meetwiki_kanban.py --sync` con le board aperte e non salvate in Obsidian.

## Obsidian + Kanban

Il vault `MeetWiki/` e' un vault Obsidian valido (`.obsidian/` versionata).
Plugin community: `obsidian-kanban` (mgmeyers) e `dataview` sono **bundled** in
`MeetWiki/.obsidian/plugins/` (file `main.js`/`manifest.json`/`styles.css` versionati).
NON servono installazioni manuali da Obsidian: basta uscire dalla Restricted mode
la prima volta (Settings -> Community plugins -> Turn on).
Owner principale del Kanban personale: variabile `MEETWIKI_OWNER` in `.env`
(default: persona piu' frequente nei partecipanti).

Source of truth dello stato Kanban: `MeetWiki/.meta/actions_status.json`.
Pipeline: `meetwiki_update.py` esegue `kanban --sync` PRIMA e `kanban --export`
DOPO, quindi i drag&drop fatti in Obsidian persistono attraverso gli update.
Le colonne riconosciute sono: `Open` | `In Progress` | `Blocked` | `Done`.

## Operazioni distruttive

Chiedere SEMPRE conferma prima di:
- `--reset` (cancella `notes/`, `topics/`, `people/`, `manifest.json`).
- Rinomine/spostamenti in `note_riunioni/archive/`.
- Modifiche al downloader (`scripts/gemini_notes_downloader.py`): puo' rompere lo scraping.
- `git push --force`, `git reset --hard`, eliminazione branch.

## Documentazione da tenere allineata

Quando una di queste cose cambia, aggiornare TUTTI i file coinvolti nella stessa PR:

- Skill o script aggiunti/rimossi → `MeetWiki/README.md` (tabella), `.github/copilot-instructions.md`, `AGENTS.md`
- Struttura cartelle → `MeetWiki/README.md` (albero) + `AGENTS.md` (invarianti)
- Comportamento ingest → `.github/skills/meetwiki-ingest/SKILL.md` + `MeetWiki/.meta/schema.md` se cambia frontmatter
- Flag CLI di `meetwiki_update.py` → `.github/skills/meetwiki-update/SKILL.md` + sezione "Comandi rapidi" di questo file

## Riferimenti rapidi

- Schema frontmatter: [MeetWiki/.meta/schema.md](MeetWiki/.meta/schema.md)
- Istruzioni Copilot: [.github/copilot-instructions.md](.github/copilot-instructions.md)
- README wiki: [MeetWiki/README.md](MeetWiki/README.md)
- Ingest principale: [scripts/meetwiki_ingest.py](scripts/meetwiki_ingest.py)
- Wrapper pipeline: [scripts/meetwiki_update.py](scripts/meetwiki_update.py)
