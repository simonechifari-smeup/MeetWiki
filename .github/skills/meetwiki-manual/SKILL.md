---
name: meetwiki-manual
description: Gestisce note manuali in `MeetWiki/manual/` (prep meeting, todo personali, progetti). Schema rilassato (solo `id`, `title`, `date` obbligatori). Action items estratti finiscono in `MY-KANBAN.md` con badge `[M]` e nell'indice BM25 di `meetwiki-ask`. Da usare quando l'utente chiede "crea nota prep", "aggiungi todo personale", "traccia progetto X", "note manuali", oppure quando vuole task fuori dal contesto di un meeting reale.
---

# Skill: meetwiki-manual

## Quando usare
- Utente chiede: "crea nota prep per X", "aggiungi todo", "traccia il progetto Y"
- Servono action items personali NON legati a un meeting Gemini reale
- Vuoi una nota nella wiki che venga indicizzata da `meetwiki-ask` ma non finisca negli indici cronologici

## Quando NON usare
- L'utente sta importando una nota da Gemini → usa `meetwiki-ingest`
- L'azione è già stata assegnata in un meeting reale → cerca con `meetwiki-search` / `meetwiki-ask`
- Serve modificare lo stato di un task esistente → usa `meetwiki-kanban`

## Struttura cartelle

```
MeetWiki/manual/
├── prep/              # preparazione meeting (es. agenda, todo prep)
│   └── 2026-06-03-allineamento-dev-ai.md
├── personal/          # todo personali, reminders
│   └── todo-week-22.md
└── projects/          # tracking progetti continuativi
    └── plugin-obsidian-meetwiki.md
```

La struttura sottostante a `manual/` è **libera** — usa quella che ha senso.

## Schema frontmatter (rilassato)

Obbligatori: `id`, `title`, `date`. Tutti gli altri opzionali.

```yaml
---
id: 2026-06-03-prep-allineamento-dev-ai
title: "Prep — Allineamento Dev AI"
date: 2026-06-03
tags:
  - prep
  - dev-ai
participants: []
related_docs: []
---
```

## Convenzioni `id`

`{YYYY-MM-DD}-{slug-kebab-case}`. La data è quella in cui la nota è rilevante
(meeting prep → data del meeting; todo → data di creazione).

## Sezione Action Items

Stessa sintassi delle note canoniche:

```markdown
## Action Items

- [ ] [Owner] Descrizione task...
- [ ] [Owner1, Owner2] Task condiviso...
- [ ] Senza owner finisce a "Non assegnato"
```

Owner = persona reale per finire nel `MY-KANBAN.md` se è l'owner principale.

## Procedura

### 1. Crea la nota
Decide path: `manual/{categoria}/{id}.md`. Scrivi frontmatter + body con sezione
`## Action Items` se servono task.

### 2. Esegui la pipeline
```powershell
.venv\Scripts\python.exe scripts\meetwiki_update.py
```

Oppure solo i passi necessari:
```powershell
.venv\Scripts\python.exe scripts\meetwiki_actions.py    # aggiorna ACTIONS.md
.venv\Scripts\python.exe scripts\meetwiki_kanban.py     # aggiorna MY-KANBAN.md
.venv\Scripts\python.exe scripts\meetwiki_ask.py --index  # indicizza per BM25
```

### 3. Verifica
- `MY-KANBAN.md` contiene card prefissate `[M]` per le tue azioni
- `ACTIONS.md` include la nota nella vista globale
- `meetwiki_ask.py "tua query"` trova passaggi dalla nota

## Comportamento con la pipeline

| Script | Tratta `manual/` come |
|--------|------------------------|
| `meetwiki_ingest.py` | Ignora (le note manuali NON vengono ingerite) |
| `meetwiki_actions.py` | Estrae action items, flag `is_manual=true` |
| `meetwiki_kanban.py` | Card con prefisso `[M]` nelle board |
| `meetwiki_ask.py` | Indicizzate nel BM25, ricercabili |
| `meetwiki_index.py` | **Escluse** da `INDEX.md`, `TAGS.md`, `PEOPLE.md` |
| `meetwiki_summarize.py` | **Escluse** da `topics/`, `people/` |
| `meetwiki_digest.py` | **Escluse** dai digest |
| `meetwiki_update.py --reset` | **Preservate** (sono tue, non rigenerabili) |

## Hash e sync Kanban

L'hash dell'action item usa la formula standard
`sha1(note_id|owner|task)[:10]`. Sincronizzazione bidirezionale
(drag&drop in Obsidian → `meetwiki_kanban.py --sync`) funziona identica alle
note normali — il prefisso `[M]` è solo display, non altera l'hash.

## Non fare

- NON mettere note manuali in `MeetWiki/notes/`: la pipeline le rigenererebbe da `manifest.json` e le perderesti.
- NON usare lo schema completo delle note canoniche con campi `source` / `source_hash`: confonde i tool. Usa lo schema rilassato.
- NON cancellare manualmente `actions_status.json`: perdi lo stato Kanban anche delle azioni manuali.

## Esempio: prep meeting

File `MeetWiki/manual/prep/2026-06-03-allineamento-dev-ai.md`:

```markdown
---
id: 2026-06-03-prep-allineamento-dev-ai
title: "Prep — Allineamento Dev AI"
date: 2026-06-03
tags:
  - prep
  - dev-ai
---

## Riepilogo

Preparazione per la riunione di allineamento Dev AI del 3 giugno,
follow-up del kickoff del 26 maggio.

## Action Items

- [ ] [Simone Chifari] Definire agenda meeting
- [ ] [Simone Chifari] Convocare partecipanti via calendar
- [ ] [Simone Chifari] Preparare bozza struttura "servizi comuni"
```

Dopo `meetwiki_update.py`:
- 3 card `[M]` in `MY-KANBAN.md` colonna `Open`
- La nota è ricercabile con `meetwiki_ask.py "allineamento dev ai"`
- `INDEX.md` resta pulito (cronologia dei soli meeting reali)
