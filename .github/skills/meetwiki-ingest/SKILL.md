---
name: meetwiki-ingest
description: Importa note di riunioni (file .md) da `note_riunioni/` dentro la wiki strutturata `MeetWiki/notes/`, aggiungendo frontmatter YAML, estraendo partecipanti, decisioni, action items e tag. Da usare quando l'utente chiede di "ingerire", "importare", "aggiornare la wiki", "processare le nuove note" o quando ci sono file in `note_riunioni/` non ancora in `MeetWiki/.meta/manifest.json`.
---

# Skill: meetwiki-ingest

## Quando usare
- Utente chiede "ingerisci le note", "aggiorna MeetWiki", "importa nuove riunioni"
- Sono presenti file `.md` in [note_riunioni/](../../note_riunioni/) non registrati in [MeetWiki/.meta/manifest.json](../../MeetWiki/.meta/manifest.json)

## Procedura

### 1. Identifica file nuovi/modificati
1. Leggi [MeetWiki/.meta/manifest.json](../../MeetWiki/.meta/manifest.json) → mappa `{filename: sha256}`
2. Elenca file in `note_riunioni/*.md`
3. Calcola hash SHA-256 di ciascuno (in PowerShell: `Get-FileHash -Algorithm SHA256`)
4. Filtra solo: nuovi OR hash diverso da manifest

### 2. Per ogni file da ingerire

#### 2a. Parsing nome file
Atteso: `YYYY-MM-DD Titolo Riunione.md` (output del downloader).
- `date` = primi 10 char
- `title_raw` = resto senza estensione
- `slug` = lowercase, spazi→`-`, rimuovi caratteri non `[a-z0-9-]`
- `id` = `{date}-{slug}` (max 80 char)

#### 2b. Estrazione contenuto
Leggi il file. Identifica:
- **Partecipanti**: sezione "Partecipanti" / "Attendees" / lista email
- **Argomenti/Decisioni/Action Items**: cerca heading o pattern `- [ ]`, "Decisione:", "Azione:"
- **Tag automatici**: 
  - dal titolo (es. "Meet Settimanale" → `meet-settimanale`)
  - parole chiave ricorrenti (es. "datacenter", "release", "incident")

#### 2c. Generazione file nota
Crea `MeetWiki/notes/{id}.md` con:

```markdown
---
id: {id}
title: "{title_raw}"
date: {date}
source: "note_riunioni/{original_filename}"
source_hash: "sha256:{hash}"
ingested_at: {ISO8601_now}
participants: [...]
tags: [...]
related_docs: [...]
---

## Riepilogo
{2-3 frasi sintetiche generate leggendo il contenuto}

## Partecipanti
{lista}

## Argomenti
{punti estratti}

## Decisioni
{decisioni estratte, o "Nessuna decisione esplicita."}

## Action Items
{checkbox list, o "Nessuna azione tracciata."}

## Trascrizione / Note originali
{contenuto grezzo del file sorgente, immutato}
```

#### 2d. Aggiorna manifest
Aggiungi/aggiorna entry in `MeetWiki/.meta/manifest.json`:
```json
"2026-05-29 DataCenter Operations.md": {
  "id": "2026-05-29-datacenter-operations",
  "hash": "abc123...",
  "ingested_at": "2026-05-29T17:10:00"
}
```

### 3. Trigger reindex
Dopo aver ingerito ≥1 nota, **invoca la skill `meetwiki-index`** per rigenerare `INDEX.md`, `TAGS.md`, `PEOPLE.md`.

## Output finale all'utente
Riepilogo conciso:
```
Ingest completato: N nuove note, M aggiornate, K saltate (già aggiornate).
Indici rigenerati.
```

## Vincoli
- **Mai sovrascrivere** la sezione "Trascrizione / Note originali" se la nota esiste già con hash diverso: archivia la vecchia in `notes/_history/{id}-{old_hash[:8]}.md` prima di sovrascrivere.
- Frontmatter YAML deve essere valido (no tab, stringhe quotate se contengono `:`).
- Hash SHA-256 calcolato sul **contenuto binario** del file sorgente.
