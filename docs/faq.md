# ❓ FAQ & Troubleshooting

## Domande frequenti

### Come faccio ad aggiornare la wiki?

```powershell
.venv\Scripts\python.exe scripts\meetwiki_update.py
```

Questo è il comando unico che fa tutto: importa note, rigenera indici, crea pagine aggregate, aggiorna action items e Kanban.

---

### Perché le note non vengono scaricate?

1. **Chrome deve essere chiuso** — lo script lo chiude e riapre automaticamente, ma processi orfani possono interferire
2. **Verifica il login Gmail** — apri Chrome manualmente e controlla di essere loggato
3. **Controlla `.cache/processed_emails.json`** — potrebbe già averle processate

---

### Come aggiungo un nuovo tag?

I tag sono gestiti dalla whitelist `KEYWORD_TAGS` in `scripts/meetwiki_ingest.py`. Aggiungi la keyword e riesegui:

```powershell
.venv\Scripts\python.exe scripts\meetwiki_update.py --force
```

---

### Posso rinominare una nota?

**No, non manualmente.** Il manifest traccia i file per path. Se devi rinominare:
1. Modifica il path in `.meta/manifest.json`
2. Rinomina il file fisicamente
3. Riesegui `meetwiki_update.py`

---

### Come chiudo un action item senza Obsidian?

Modifica `MeetWiki/.meta/actions_status.json` aggiungendo l'hash dell'action:

```json
{
  "hash10cifre": {
    "status": "done",
    "closed_at": "2026-05-29"
  }
}
```

Usa `meetwiki_actions.py --list` per vedere gli hash.

---

### Il Kanban non si sincronizza

- Assicurati di **salvare (Ctrl+S)** la board in Obsidian prima di chiuderlo
- Non eseguire `meetwiki_kanban.py --sync` con Obsidian aperto e la board non salvata
- Non cancellare le ancore `^h{hash}` alla fine delle card

---

### Il downloader non trova Chrome

Verifica il percorso in `.env`:

```env
CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe
```

Se Chrome è installato in un percorso diverso, aggiorna la variabile.

---

### Come resetto tutto e ricomincio da zero?

⚠️ **Operazione distruttiva** — cancella note, indici e manifest:

```powershell
.venv\Scripts\python.exe scripts\meetwiki_update.py --reset
```

Nota: `.meta/actions_status.json` (override manuali) NON viene cancellato.

---

### Posso usare il progetto su Linux?

Il downloader (`gemini_notes_downloader.py`) è specifico per Windows (percorsi Chrome, task scheduler). La pipeline wiki (`meetwiki_*.py`) è portabile ma non testata su Linux.

---

## Errori comuni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| `Chrome not found` | Percorso errato in `.env` | Aggiorna `CHROME_EXE` |
| `Cannot connect to Chrome` | Chrome occupato/non chiuso | Chiudi Chrome manualmente |
| `Manifest not found` | Primo avvio o reset | Esegui `meetwiki_update.py` |
| `Unstaged changes` | Git filter-branch con file modificati | `git add .` prima |
| `Permission denied` su `.cache/` | File lockato | Chiudi processi che lo usano |
