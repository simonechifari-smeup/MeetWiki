---
name: meetwiki-digest
description: Genera digest periodici delle riunioni in `MeetWiki/digests/weekly/YYYY-Www.md` (settimanali) o `MeetWiki/digests/monthly/YYYY-MM.md` (mensili). Ogni digest contiene riunioni del periodo, action items nuovi/chiusi, tag attivi (con delta vs periodo precedente) e persone più coinvolte. Da usare quando l'utente chiede "digest settimanale", "riepilogo della settimana", "cosa è successo a maggio", "report mensile", "status report".
---

# Skill: meetwiki-digest

## Quando usare
- Utente chiede: "digest", "riepilogo settimana/mese", "status report", "cosa è successo", "report periodico"
- Pianificazione retrospettive / standup
- Dopo `meetwiki-ingest` per refresh dei digest aperti

## Output

- `MeetWiki/digests/weekly/YYYY-Www.md` — settimana ISO (lunedì-domenica)
- `MeetWiki/digests/monthly/YYYY-MM.md` — mese solare

Frontmatter: `type: digest`, `period`, `period_start`, `period_end`, `meetings_count`, `generated_at`.

## Comandi

```powershell
# Settimana corrente
.venv\Scripts\python.exe scripts\meetwiki_digest.py

# Mese corrente
.venv\Scripts\python.exe scripts\meetwiki_digest.py --period month

# Settimana specifica (qualunque data dentro)
.venv\Scripts\python.exe scripts\meetwiki_digest.py --date 2026-05-20

# Mese specifico
.venv\Scripts\python.exe scripts\meetwiki_digest.py --period month --date 2026-04-15

# Rigenera TUTTI i digest storici (uno per ogni periodo con almeno una nota)
.venv\Scripts\python.exe scripts\meetwiki_digest.py --all
.venv\Scripts\python.exe scripts\meetwiki_digest.py --period month --all
```

## Contenuto del digest

1. **Riunioni** del periodo con riepilogo breve + tag
2. **Action items nuovi** (max 50) con citazione nota
3. **Action items chiusi** (max 30, basato su `- [x]` nelle note)
4. **Tag più attivi** con freccia ↑/↓/→ vs periodo precedente
5. **Persone più coinvolte** (top 15)

## Verifiche post-esecuzione
- File output esiste in `digests/weekly/` o `digests/monthly/`
- Frontmatter ha `period` corretto (formato `YYYY-Www` o `YYYY-MM`)
- `meetings_count` matcha le righe `- **YYYY-MM-DD**` nel body

## Note importanti
- I link alle note usano path relativi `../../notes/...` (da `digests/{weekly|monthly}/`)
- Settimane in formato **ISO 8601** (W01 = settimana col primo giovedì dell'anno)
- Se non ci sono riunioni nel periodo, il digest viene comunque scritto (sezione "_Nessuna riunione in questo periodo._")

## Integrazione
- Eseguito da `meetwiki_update.py` (con `--all` per entrambi i periodi).
- Saltabile con `--skip-digest` su `meetwiki_update.py`.
