# 🚀 Utilizzo

## Workflow quotidiano

```powershell
# Scarica nuove note da Gmail
run.bat

# Aggiorna la wiki (pipeline completa)
.venv\Scripts\python.exe scripts\meetwiki_update.py
```

Questo è tutto per l'uso giornaliero. La pipeline si occupa di tutto: importazione, indicizzazione, generazione pagine aggregate, action items e Kanban.

---

## Comandi principali

### Pipeline completa

```powershell
# Update standard (caso 99%)
.venv\Scripts\python.exe scripts\meetwiki_update.py

# Re-ingest forzato (dopo modifica tag o template)
.venv\Scripts\python.exe scripts\meetwiki_update.py --force

# Pipeline veloce (salta digest e search index)
.venv\Scripts\python.exe scripts\meetwiki_update.py --skip-digest --skip-search

# Pulizia pagine aggregate stale
.venv\Scripts\python.exe scripts\meetwiki_update.py --clean

# Anteprima senza scritture (dry-run)
.venv\Scripts\python.exe scripts\meetwiki_update.py --dry-run
```

### Ricerca

```powershell
# Ricerca semantica (linguaggio naturale)
.venv\Scripts\python.exe scripts\meetwiki_ask.py "decisioni su acronis"

# Con filtri
.venv\Scripts\python.exe scripts\meetwiki_ask.py --tag data-center --since 2026-05-01 "patch management"
```

### Action items

```powershell
# Rigenera tracker
.venv\Scripts\python.exe scripts\meetwiki_actions.py

# Lista action items con hash
.venv\Scripts\python.exe scripts\meetwiki_actions.py --list
```

### Ingest

```powershell
# Solo ingest, con log dettagliato (utile per debug tag)
.venv\Scripts\python.exe scripts\meetwiki_ingest.py --verbose

# Anteprima ingest senza scritture
.venv\Scripts\python.exe scripts\meetwiki_ingest.py --dry-run
```

### Kanban

```powershell
# Sync + export (default sicuro)
.venv\Scripts\python.exe scripts\meetwiki_kanban.py

# Solo sync da Obsidian → status
.venv\Scripts\python.exe scripts\meetwiki_kanban.py --sync

# Solo rigenera board
.venv\Scripts\python.exe scripts\meetwiki_kanban.py --export
```

### Digest

```powershell
# Digest settimana corrente
.venv\Scripts\python.exe scripts\meetwiki_digest.py

# Digest mese corrente
.venv\Scripts\python.exe scripts\meetwiki_digest.py --period month

# Tutti i digest storici
.venv\Scripts\python.exe scripts\meetwiki_digest.py --all
```

---

## Skill Copilot

Se usi VS Code con GitHub Copilot, le skill sono disponibili direttamente in chat:

| Skill | Uso |
|-------|-----|
| `meetwiki-update` | "aggiorna la wiki" |
| `meetwiki-search` | "cerca riunioni su X" |
| `meetwiki-ask` | "cosa abbiamo deciso su Y?" |
| `meetwiki-actions` | "lista action items aperti" |
| `meetwiki-digest` | "digest della settimana" |
| `meetwiki-kanban` | "rigenera il mio kanban" |
| `meetwiki-ingest` | "importa le nuove note" |
| `meetwiki-index` | "rigenera gli indici" |
| `meetwiki-summarize` | "crea pagina riassunto su Z" |

---

## Sviluppo e test

```powershell
# Esegui la suite di test
.venv\Scripts\python.exe -m pytest -q

# Linting
.venv\Scripts\python.exe -m ruff check scripts/
.venv\Scripts\python.exe -m ruff check scripts/ --fix
```

---

## Gestione dello stato

### Chiudere un action item manualmente

Modifica `MeetWiki/.meta/actions_status.json`:

```json
{
  "abc1234567": {
    "status": "done",
    "closed_at": "2026-05-29",
    "note": "Completato nella call di venerdì"
  }
}
```

### Drag & drop in Obsidian

Sposta le card tra colonne (`Open` → `Done`) e salva. Al prossimo `meetwiki_update.py`, lo stato viene sincronizzato automaticamente.
