---
name: meetwiki-kanban
description: Gestisce le board Kanban Obsidian per gli action items. Esporta `MeetWiki/MY-KANBAN.md` (board personale dell'owner principale da `MEETWIKI_OWNER` in `.env`) e `MeetWiki/actions/kanban/{owner}.md` (board per ogni altro owner) nel formato del plugin `obsidian-kanban`. Supporta **sync bidirezionale**: drag&drop tra colonne in Obsidian → `--sync` aggiorna `MeetWiki/.meta/actions_status.json`. Da usare quando l'utente chiede "apri il mio kanban", "rigenera board", "sincronizza Obsidian", "sposta task X in done".
---

# Skill: meetwiki-kanban

## Quando usare
- Utente chiede: "kanban", "board", "il mio kanban", "rigenera board"
- Dopo che l'utente ha mosso card in Obsidian e vuole persistere lo stato
- Prima di rigenerare i tracker (`meetwiki-actions`) per non perdere modifiche del Kanban

## Output

- `MeetWiki/MY-KANBAN.md` — **board personale** dell'owner principale (priorità nell'UI Obsidian)
- `MeetWiki/actions/kanban/{owner-slug}.md` — una board per ogni altro owner
- Aggiorna `MeetWiki/.meta/actions_status.json` quando si esegue `--sync`

## Owner principale
- Letto da `MEETWIKI_OWNER` in `.env` (default: la persona più frequente nei partecipanti)
- Determina quale board diventa `MY-KANBAN.md`
- Match flessibile: card con owner `"Simone Chifari, Andrea Bortolan"` finiscono comunque nella board di Simone se è l'owner principale (match per substring + nome)

## Comandi

```powershell
# Default: sync + export (sicuro, raccomandato)
.venv\Scripts\python.exe scripts\meetwiki_kanban.py

# Solo rigenera dalle ultime modifiche dello status (NON legge le board)
.venv\Scripts\python.exe scripts\meetwiki_kanban.py --export

# Solo legge le board e aggiorna lo status (NON rigenera i file)
.venv\Scripts\python.exe scripts\meetwiki_kanban.py --sync

# Solo board personale, niente per-owner
.venv\Scripts\python.exe scripts\meetwiki_kanban.py --export --me-only
```

## Workflow utente tipico

1. **Lunedì mattina**: apri `MeetWiki/MY-KANBAN.md` in Obsidian (plugin Kanban → "Open as Kanban board")
2. Trascina card da `Open` → `In Progress` / `Blocked` / `Done` durante la settimana
3. Prima di chiudere Obsidian (o prima di `meetwiki-update`), esegui:
   ```powershell
   .venv\Scripts\python.exe scripts\meetwiki_kanban.py --sync
   ```
   Lo stato viene scritto in `.meta/actions_status.json` e persiste.

**`meetwiki_update.py` esegue automaticamente `--sync` PRIMA dell'ingest e `--export` DOPO**, quindi normalmente non serve invocarlo a mano.

## Colonne supportate

| Colonna board   | Status JSON   |
|-----------------|---------------|
| `Open`          | `open`        |
| `In Progress`   | `in_progress` |
| `Blocked`       | `blocked`     |
| `Done`          | `done`        |

Spostare una card in `Done` aggiunge automaticamente `closed_at` (data corrente) e `note: "Chiuso da Kanban"` allo status JSON.

## Formato card (importante per il sync)

```markdown
- [ ] Descrizione task  [↗](notes/2026-05/x.md) ^h{hash10}
```

L'ancora `^h{hash10}` è un **block reference Obsidian** ed è l'identificatore stabile della card.
- **NON** rimuoverla: senza hash il sync non riconosce la card.
- **NON** duplicare l'hash: una card per hash.
- Il testo del task può essere modificato a mano in Obsidian (verrà sovrascritto al prossimo `--export` se cambia nella nota sorgente).

## Verifiche post-esecuzione

- `MY-KANBAN.md` esiste e contiene le 4 colonne `Open / In Progress / Blocked / Done`
- Frontmatter ha `kanban-plugin: board` (richiesto dal plugin)
- `actions/kanban/` contiene una board per ogni owner con almeno 1 azione

## Non fare

- NON eseguire `--sync` con le board aperte in Obsidian non salvate: salva sempre (Ctrl+S) prima.
- NON cancellare manualmente `actions_status.json`: perdi tutto lo stato Kanban. Anche `meetwiki_update --reset` lo cancella → conferma all'utente prima di lanciarlo.
- NON modificare a mano `MY-KANBAN.md` con editor non-Obsidian per cambiare colonne: usa l'UI Kanban (più sicuro per il parsing).

## Plugin Obsidian richiesti

**Bundled nel repo** in `MeetWiki/.obsidian/plugins/`:
- `obsidian-kanban` (mgmeyers) — file `main.js` / `manifest.json` / `styles.css` versionati
- `dataview` — stesso schema

L'utente NON deve installare nulla da Obsidian. Al primo avvio del vault deve solo:
1. *Settings → Community plugins → Turn on community plugins* (esce dalla Restricted mode)
2. Verificare che `Kanban` e `Dataview` siano attivi (di solito già ON grazie a `community-plugins.json`)

Se la cartella del plugin viene cancellata, reinstalla da CLI:
```powershell
$dir = 'MeetWiki\.obsidian\plugins\obsidian-kanban'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$rel = Invoke-RestMethod 'https://api.github.com/repos/mgmeyers/obsidian-kanban/releases/latest' -Headers @{ 'User-Agent'='meetwiki' }
foreach ($n in 'main.js','manifest.json','styles.css') {
  $a = $rel.assets | Where-Object name -eq $n | Select-Object -First 1
  Invoke-WebRequest -Uri $a.browser_download_url -OutFile (Join-Path $dir $n) -UseBasicParsing
}
```

## Integrazione

- Eseguito automaticamente da `meetwiki_update.py` (sync prima, export dopo).
- Saltabile con `--skip-kanban` su `meetwiki_update.py`.
- `actions_status.json` è condiviso con `meetwiki-actions` (stessa source of truth).
