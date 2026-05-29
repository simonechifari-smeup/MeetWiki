---
name: meetwiki-summarize
description: Genera pagine aggregate `topics/{tag}.md` o `people/{persona}.md` nella MeetWiki, sintetizzando tutte le riunioni che condividono un tag o un partecipante. Da usare quando l'utente chiede "crea pagina riassunto su X", "genera profilo di Y", "fai una sintesi del tema Z".
---

# Skill: meetwiki-summarize

## Quando usare
- "Crea una pagina riassuntiva sul tema X"
- "Genera il profilo di partecipazione di Mario Rossi"
- "Sintetizza tutto quello che sappiamo su <topic>"
- Periodicamente per consolidare conoscenza

## Procedura

### Modalità A — Pagina topic (`topics/{tag}.md`)

1. Identifica il tag (chiedi all'utente se ambiguo; usa `TAGS.md` per lista valida)
2. Trova tutte le note con quel tag nel frontmatter
3. Per ciascuna estrai: titolo, data, riepilogo, decisioni, action items
4. Genera `MeetWiki/topics/{tag}.md`:

```markdown
---
type: topic
tag: data-center
generated_at: 2026-05-29T17:30:00
notes_count: 12
---

# Topic: data-center

## Sintesi globale
{3-5 paragrafi che consolidano i temi ricorrenti, decisioni chiave,
evoluzione nel tempo, partecipanti principali}

## Decisioni cumulate
{lista cronologica di tutte le decisioni dalle note}

## Action items aperti
{tutti i `- [ ]` non spuntati, raggruppati per assegnatario}

## Note correlate (cronologico)
- 2026-05-29 — [DataCenter Operations](../notes/2026-05-29-...md)
- ...
```

### Modalità B — Pagina persona (`people/{slug}.md`)

1. Identifica persona (slug dal nome: "Mario Rossi" → `mario-rossi`)
2. Trova note dove `participants` contiene quel nome
3. Genera `MeetWiki/people/{slug}.md`:

```markdown
---
type: person
name: Mario Rossi
slug: mario-rossi
generated_at: 2026-05-29T17:30:00
meetings_count: 15
---

# Mario Rossi

## Aree di attività
{tag più frequenti nelle riunioni a cui ha partecipato}

## Action items assegnati
- [ ] {azione} — da [meet 2026-05-29](../notes/...md)

## Decisioni in cui è coinvolto
{lista}

## Riunioni (cronologico)
- 2026-05-29 — [Titolo](../notes/...md)
```

## Vincoli
- **Non duplicare** contenuto delle note: linkalo
- I file in `topics/` e `people/` sono **rigenerabili** — il frontmatter `generated_at` lo segnala
- Se l'utente modifica manualmente, preserva sezioni custom marcate con `<!-- custom-start -->...<!-- custom-end -->`
- Action items: estrai solo quelli con sintassi `- [ ]` (non `- [x]`)

## Output finale
```
Generato MeetWiki/topics/{tag}.md (N note aggregate, M action items).
```
