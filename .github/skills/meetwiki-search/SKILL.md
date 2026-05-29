---
name: meetwiki-search
description: Cerca e risponde a domande sulle riunioni della MeetWiki. Da usare quando l'utente chiede "cosa abbiamo deciso su X", "chi ha partecipato a Y", "trova riunioni su Z", "quali action items sono aperti", "riassumi le riunioni della settimana". Cerca in `MeetWiki/notes/` con grep e cita le fonti.
---

# Skill: meetwiki-search

## Quando usare
- Domande informative sulle riunioni: "cosa è stato deciso", "chi ha detto X"
- "Trova le note dove si parla di ..."
- "Quali action items sono assegnati a Y"
- "Cosa è successo nelle riunioni di maggio"

## Procedura

### 1. Determina lo scope
- **Per data**: limita a `notes/YYYY-MM-*.md` o filtra frontmatter `date:`
- **Per persona**: usa `MeetWiki/PEOPLE.md` per trovare i file rilevanti
- **Per tag**: usa `MeetWiki/TAGS.md`
- **Per parola chiave**: grep su `notes/*.md`

### 2. Strategia di ricerca

1. **Prima**: leggi `MeetWiki/INDEX.md` per orientamento generale
2. **Poi**: `grep_search` con regex su `notes/` per le keyword della domanda
3. **Estrai** le sezioni rilevanti delle note matchate (massimo 5 note)
4. **Sintetizza** la risposta citando ogni fonte come link Markdown:
   ```
   ...come deciso nel [meet del 2026-05-29](MeetWiki/notes/2026-05-29-datacenter-operations.md)...
   ```

### 3. Tipi di query speciali

#### "Action items aperti"
- `grep_search` per `- [ ]` in tutte le note
- Raggruppa per `@persona` (estraggi dalla riga)
- Output: tabella `| Persona | Azione | Da nota | Scadenza |`

#### "Riassunto settimana/mese"
- Filtra note per range di date
- Per ciascuna estrai sezione `## Riepilogo`
- Output: lista cronologica + meta-sintesi finale (3-5 bullet)

#### "Chi ha partecipato a X"
- Cerca nota di X, leggi frontmatter `participants:`

## Formato risposta
- **Risposta diretta** alla domanda in 1-3 frasi
- **Fonti** come link cliccabili a `MeetWiki/notes/...`
- Mai inventare informazioni: se non trovi, dillo esplicitamente

## Vincoli
- **Non modificare** file della wiki durante una ricerca
- Cita **sempre** la nota di provenienza
- Limita a max 5 fonti per non sovraccaricare il contesto
