---
name: meetwiki-ask
description: Risponde a domande complesse sulle riunioni usando un indice di ricerca BM25 (in `MeetWiki/.meta/search_index.json`) che recupera i passaggi più rilevanti delle note. Migliore di `meetwiki-search` quando la query è in linguaggio naturale, contiene sinonimi o non sai le parole esatte. Da usare quando l'utente chiede "cosa abbiamo deciso su X", "trova passaggi su Y", "approfondisci Z", o vuole una risposta sintetica basata su più note.
---

# Skill: meetwiki-ask

## Quando usare
- Domande in linguaggio naturale che richiedono ranking di rilevanza
- L'utente chiede "cosa abbiamo deciso/discusso su X", "approfondisci Y", "dimmi tutto su Z"
- Confronto/sintesi tra più note (la query potrebbe matchare passaggi in note diverse)
- Quando `meetwiki-search` (grep) sarebbe troppo rigido (sinonimi, parole non esatte)

## Differenza vs `meetwiki-search`
| Aspetto | `meetwiki-search` | `meetwiki-ask` |
|---|---|---|
| Tecnica | grep su testo | BM25 con tokenizzazione + IDF |
| Match | esatto, case-insensitive | parole stem-like, stopword removal |
| Output | linee/file | chunk con score di rilevanza + citazioni |
| Indice | nessuno | `MeetWiki/.meta/search_index.json` |
| Quando | so esattamente cosa cerco | domanda generica / sinonimi |

## Procedura

### 1. (Se serve) Costruisci/aggiorna l'indice
```powershell
.venv\Scripts\python.exe scripts\meetwiki_ask.py --index
```
L'indice viene aggiornato automaticamente da `meetwiki_update.py`. Se le note sono cambiate dopo l'ultimo update, ricostruiscilo.

### 2. Esegui la query
```powershell
.venv\Scripts\python.exe scripts\meetwiki_ask.py "decisioni su acronis"
.venv\Scripts\python.exe scripts\meetwiki_ask.py -k 8 "trasferta faenza backup"
```

### 3. Filtri opzionali
```powershell
# Solo note con un tag specifico
.venv\Scripts\python.exe scripts\meetwiki_ask.py --tag data-center "patch management"

# Solo note in un intervallo di date
.venv\Scripts\python.exe scripts\meetwiki_ask.py --since 2026-05-01 --until 2026-05-31 "kickoff"

# Solo note con una persona specifica fra i partecipanti
.venv\Scripts\python.exe scripts\meetwiki_ask.py --person "Mantovanelli" "trasferta"
```

### 4. Usa i risultati per rispondere all'utente
L'output è un set di chunk con:
- Header: `[YYYY-MM-DD] Titolo nota — _Sezione_ (score X.XX)`
- Path della nota
- Testo del chunk (citabile direttamente)

**Cita SEMPRE le note di provenienza nella risposta all'utente** (link relativi).

## Cosa indicizza
Solo sezioni canoniche generate da `meetwiki-ingest`:
- `Metadati` (titolo + tags + partecipanti — boost per match diretto)
- `Riepilogo`
- `Partecipanti`
- `Argomenti`
- `Decisioni`
- `Action Items`

**NON** indicizza la sezione `Trascrizione / Note originali` (troppo rumorosa).

## Verifiche post-esecuzione
- `MeetWiki/.meta/search_index.json` esiste
- Il numero di chunk stampato è coerente (~10 chunk per nota in media)
- I primi 1-2 risultati sono effettivamente pertinenti alla query (altrimenti riformula)

## Quando i risultati sono scarsi
- Ricostruisci l'indice (`--index`) se hai modificato note
- Prova a rimuovere stopword o parole troppo generiche dalla query
- Usa `--tag` o `--person` per restringere se hai molte note
- Aumenta `-k` per più candidati

## Non fare
- NON editare `MeetWiki/.meta/search_index.json`: viene rigenerato.
- NON aggiungere dipendenze (sentence-transformers, faiss, chromadb): l'indice è puro Python intenzionalmente. Vedi `AGENTS.md`.

## Integrazione
- Indice ricostruito automaticamente da `meetwiki_update.py`.
- Saltabile con `--skip-search` su `meetwiki_update.py`.
