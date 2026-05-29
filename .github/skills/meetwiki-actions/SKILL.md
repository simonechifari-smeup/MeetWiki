---
name: meetwiki-actions
description: Aggrega gli action items di tutte le note in `MeetWiki/ACTIONS.md` (vista globale per persona) e `MeetWiki/actions/by-owner/{slug}.md` (una pagina per owner). Supporta override manuale dello stato (`open`/`done`) tramite `MeetWiki/.meta/actions_status.json`. Da usare quando l'utente chiede "lista action items", "cosa devo fare", "azioni aperte di X", "chiudi action item Y", "aggiorna tracker azioni".
---

# Skill: meetwiki-actions

## Quando usare
- Utente chiede: "action items aperti", "cosa deve fare X", "lista todo", "tracker azioni"
- Dopo `meetwiki-ingest` (nuove azioni potrebbero esserci)
- Dopo aver chiuso manualmente un action item (vedi sezione "Chiudere un task")

## Output

### File generati
- `MeetWiki/ACTIONS.md` — vista globale: header con totali, aperti raggruppati per owner, ultimi chiusi
- `MeetWiki/actions/by-owner/{slug}.md` — una pagina per ogni owner con aperti + chiusi

### File di stato (NON generato, persistente, editabile a mano)
- `MeetWiki/.meta/actions_status.json` — mappa `{hash: {status, closed_at, note}}`

## Procedura

### 1. Esegui lo script
```powershell
.venv\Scripts\python.exe scripts\meetwiki_actions.py
```

Per elencare a video tutti gli action items con il loro hash:
```powershell
.venv\Scripts\python.exe scripts\meetwiki_actions.py --list
```

### 2. Logica di estrazione
Lo script legge la sezione `## Action Items` di ogni nota in `MeetWiki/notes/`.
Riconosce due formati di owner:
- `- [ ] [Nome Cognome] Descrizione task`
- `- [ ] Nome Cognome: Descrizione task`

Se nessun owner riconosciuto → `Non assegnato`.

Ogni action item ha un hash a 10 caratteri deterministico su `(note_id, owner, task)`.

### 3. Chiudere un action item (workflow utente)
1. Trova l'hash con `--list` o in `ACTIONS.md`
2. Apri `MeetWiki/.meta/actions_status.json` (creato vuoto al primo run)
3. Aggiungi entry:
   ```json
   {
     "a1b2c3d4e5": { "status": "done", "closed_at": "2026-05-29", "note": "Completato in PR #123" }
   }
   ```
4. Ri-esegui lo script (o `meetwiki_update.py`)

## Verifiche post-esecuzione
- `ACTIONS.md` esiste e ha frontmatter `type: actions-global`
- `actions/by-owner/` contiene una pagina per owner
- Il numero "totali" stampato matcha la somma delle righe `- [ ]`/`- [x]` nelle note

## Non fare
- NON editare manualmente `ACTIONS.md` o `actions/by-owner/*.md`: sono sovrascritti.
- NON cambiare l'hash di un action item: si rompe l'override (l'hash dipende da `note_id + owner + task`).
- Se modifichi il testo di un action item in una nota, il suo hash cambia: l'override precedente diventa orfano.

## Integrazione
- Eseguito automaticamente da `meetwiki_update.py`.
- L'override file `actions_status.json` NON viene mai cancellato dalla pipeline (anche con `--reset`).
