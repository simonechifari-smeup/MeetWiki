---
name: meetwiki-update
description: Pipeline completa di aggiornamento della MeetWiki. Esegue in sequenza ingest delle nuove note da `note_riunioni/`, rigenerazione di `INDEX.md`/`TAGS.md`/`PEOPLE.md` e generazione delle pagine aggregate `topics/` e `people/`. Da usare quando l'utente chiede "aggiorna la wiki", "fai update completo", "rigenera tutto", "rifai la wiki", "esegui pipeline meetwiki" o vuole un singolo comando che faccia tutto.
---

# Skill: meetwiki-update

Orchestratore della pipeline MeetWiki. Sostituisce l'invocazione manuale di
`meetwiki-ingest` + `meetwiki-index` + `meetwiki-summarize`.

## Quando usare
- Utente chiede "aggiorna la wiki", "update completo", "rigenera tutto", "rifai la wiki"
- Sono stati appena scaricati nuovi file in `note_riunioni/` (output del downloader)
- E' stata modificata la taxonomia (`KEYWORD_TAGS` in `scripts/meetwiki_ingest.py`) e serve un rebuild

## Quando NON usare
- Solo ricerca/Q&A → usa `meetwiki-search`
- Solo rigenerazione indici senza re-ingest → usa `meetwiki-index`
- Generazione di una singola pagina topic/persona → usa `meetwiki-summarize`

## Procedura

Eseguire i tre script Python in sequenza, fermandosi al primo errore.
Tutti gli script sono idempotenti e usano `MeetWiki/.meta/manifest.json`
per il dedup hash-based.

### Comando unico (PowerShell)

```powershell
$py = ".venv\Scripts\python.exe"
& $py scripts\meetwiki_ingest.py
if ($LASTEXITCODE -ne 0) { throw "ingest fallito" }
& $py scripts\meetwiki_index.py
if ($LASTEXITCODE -ne 0) { throw "index fallito" }
& $py scripts\meetwiki_summarize.py
if ($LASTEXITCODE -ne 0) { throw "summarize fallito" }
```

In alternativa, esiste il wrapper [scripts/meetwiki_update.py](../../scripts/meetwiki_update.py):

```powershell
.venv\Scripts\python.exe scripts\meetwiki_update.py
```

### Flag opzionali

- `--force`: passato a `meetwiki_ingest.py`, bypassa il check hash e
  re-ingerisce TUTTE le note. Usare dopo modifiche a `KEYWORD_TAGS`,
  al template di `build_note()` o per rigenerare da zero.
- `--clean`: cancella prima `MeetWiki/topics/*.md` e `MeetWiki/people/*.md`
  (pagine aggregate stale dopo cambi di tag/dedup). NON cancella `notes/`
  ne' `manifest.json`.
- `--reset`: distruttivo. Cancella `notes/*.md`, `topics/*.md`,
  `people/*.md` e `manifest.json`. Equivale a re-ingest from scratch.
  Chiedere conferma all'utente prima di usarlo.

## Output atteso

Tre blocchi sequenziali:

```
Trovati N file in note_riunioni/
  [NUOVA|AGGIORNATA|DUP-LANG] ...
Ingest completato: X nuove, Y aggiornate, Z saltate.

Indici rigenerati: N note, M tag, K persone.

Topic generati: T (saltati U con <2 note).
Persone generate: P (saltate Q con <2 riunioni).
```

## Errori comuni

| Errore | Causa | Fix |
|---|---|---|
| `ModuleNotFoundError` | venv non attivo | usare path esplicito `.venv\Scripts\python.exe` |
| Pagine `topics/` o `people/` obsolete dopo rinomina tag | summarize non cancella file morti | usare `--clean` |
| Note duplicate EN/IT | manifest non aggiornato | il dedup `select_canonical` registra `dup_of`; rerun risolve |
| Hash non cambia ma serve re-ingest | modifica a template/tag | usare `--force` |

## Note di design

- L'ordine e' rigido: `ingest` produce/aggiorna `notes/*.md`, `index`
  legge il loro frontmatter, `summarize` legge sia frontmatter sia
  contenuto delle note. Invertire l'ordine produce pagine vuote o stale.
- `ingest` e' l'unico step che scrive in `notes/` e in
  `MeetWiki/.meta/manifest.json`.
- `index` e `summarize` sono puri rigeneratori: cancellarne l'output e
  rilanciarli e' sempre sicuro.
