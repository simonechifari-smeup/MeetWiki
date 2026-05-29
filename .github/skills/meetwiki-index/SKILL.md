---
name: meetwiki-index
description: Rigenera gli indici `INDEX.md` (cronologico), `TAGS.md` (per tag) e `PEOPLE.md` (per partecipante) della MeetWiki leggendo il frontmatter di tutte le note in `MeetWiki/notes/`. Da usare dopo `meetwiki-ingest`, dopo modifiche manuali alle note, o quando l'utente chiede "rigenera indici", "aggiorna TOC".
---

# Skill: meetwiki-index

## Quando usare
- Dopo `meetwiki-ingest`
- Utente chiede "rigenera indici", "aggiorna il sommario", "rebuild TOC"
- Dopo modifica manuale di frontmatter (tag, partecipanti)

## Procedura

### 1. Scansiona note
Leggi tutti i file `MeetWiki/notes/*.md` (escludi `_history/`).
Per ognuno estrai dal frontmatter: `id`, `title`, `date`, `participants`, `tags`.

### 2. Genera `MeetWiki/INDEX.md`

```markdown
# Indice cronologico

> Generato da `meetwiki-index` il {ISO8601_now}. Non modificare a mano.

## 2026

### Maggio
- 2026-05-29 — [DataCenter Operations — Meet Settimanale](notes/2026-05-29-datacenter-operations.md)
- 2026-05-28 — [Release Planning](notes/2026-05-28-release-planning.md)

### Aprile
...
```

Raggruppa per **anno** e **mese**, ordina **discendente** (più recente prima).

### 3. Genera `MeetWiki/TAGS.md`

```markdown
# Indice per tag

> Generato da `meetwiki-index` il {ISO8601_now}.

## data-center (12)
- 2026-05-29 — [DataCenter Operations](notes/2026-05-29-datacenter-operations.md)
- ...

## meet-settimanale (8)
- ...
```

Tag ordinati per **frequenza decrescente**. Conteggio nel titolo.

### 4. Genera `MeetWiki/PEOPLE.md`

```markdown
# Indice partecipanti

> Generato da `meetwiki-index` il {ISO8601_now}.

## Mario Rossi (15 riunioni)
- 2026-05-29 — [DataCenter Operations](notes/2026-05-29-datacenter-operations.md)
- ...

## Anna Bianchi (9 riunioni)
- ...
```

Persone ordinate per **numero di riunioni decrescente**.

## Output finale
```
Indici rigenerati: N note indicizzate, T tag distinti, P persone distinte.
```

## Vincoli
- Tutti i path sono **relativi** alla root `MeetWiki/`
- Non toccare file in `notes/` né `topics/` né `people/`
- Se un frontmatter è malformato: logga warning, salta la nota, continua
