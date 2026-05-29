# ⚙️ Setup

## Prerequisiti

- **Windows 10/11**
- **Python 3.11+** (testato con 3.14)
- **Google Chrome** installato e loggato con il tuo account Google
- **Git** (opzionale, per versionamento)
- **Obsidian** (opzionale, per Kanban e navigazione vault)

## Installazione

### 1. Clona il repository

```powershell
git clone https://github.com/simonechifari-smeup/MeetWiki.git
cd MeetWiki
```

### 2. Esegui il setup automatico

```powershell
scripts\setup.bat
```

Questo script esegue in sequenza:
1. Crea l'ambiente virtuale `.venv/`
2. Installa le dipendenze da `requirements.txt` (Playwright, python-dotenv)
3. Installa il browser Chromium via Playwright
4. Copia `.env.example` → `.env` (se non esiste)
5. Crea le cartelle necessarie (`note_riunioni/`, `.cache/`, `MeetWiki/.meta/`)

### 3. Configura il file `.env`

Modifica `.env` con i tuoi valori:

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `OUTPUT_DIR` | Percorso cartella dove salvare le note scaricate | `./note_riunioni` |
| `MEETWIKI_OWNER` | Il tuo nome per la board Kanban personale | (auto-detect) |
| `CHROME_USER_DATA` | Percorso User Data di Chrome | `%LOCALAPPDATA%\Google\Chrome\User Data` |
| `CHROME_PROFILE` | Profilo Chrome da utilizzare | `Default` |
| `CHROME_EXE` | Percorso eseguibile Chrome | `C:\Program Files\Google\Chrome\Application\chrome.exe` |
| `GITHUB_MODELS_TOKEN` | Token GitHub per Obsidian Copilot (opzionale) | — |

### 4. Verifica installazione

```powershell
.venv\Scripts\python.exe -c "from playwright.sync_api import sync_playwright; print('OK')"
```

---

## Setup Vault Obsidian

I plugin sono già inclusi nel repository (bundled in `MeetWiki/.obsidian/plugins/`). In caso di clone fresco o aggiornamento plugin:

```powershell
scripts\setup_obsidian.bat
```

Questo script:
1. Crea la struttura completa del vault (`notes/`, `topics/`, `people/`, `actions/`, `digests/`)
2. Genera `community-plugins.json` con i plugin necessari
3. Scarica **obsidian-kanban** dall'ultima release GitHub
4. Scarica **dataview** dall'ultima release GitHub

### Plugin inclusi

| Plugin | Repo | Funzione |
|--------|------|----------|
| `obsidian-kanban` | [mgmeyers/obsidian-kanban](https://github.com/mgmeyers/obsidian-kanban) | Board Kanban per action items |
| `dataview` | [blacksmithgu/obsidian-dataview](https://github.com/blacksmithgu/obsidian-dataview) | Query strutturate nelle pagine aggregate |
| `copilot` | [logancyang/obsidian-copilot](https://github.com/logancyang/obsidian-copilot) | Chat AI sulla wiki (richiede `GITHUB_MODELS_TOKEN`) |

### Attivazione in Obsidian

1. Apri Obsidian → *Open folder as vault* → seleziona `MeetWiki/`
2. Settings → Community plugins → **Turn on community plugins**
3. Verifica che `Kanban`, `Dataview` siano attivi (toggle verde)
4. **Non serve scaricare nulla** da Obsidian: i plugin sono già a disco

---

## Schedulazione automatica (opzionale)

Per scaricare le note in automatico ogni giorno:

```powershell
scripts\schedule_task.bat
```

Crea un task di Windows Task Scheduler che esegue `run.bat` all'orario configurato.

---

## Riepilogo script

| Script | Scopo |
|--------|-------|
| `scripts\setup.bat` | Setup completo: venv + dipendenze + Playwright + .env + cartelle |
| `scripts\setup_obsidian.bat` | Setup vault Obsidian: struttura + download plugin da GitHub |
| `scripts\schedule_task.bat` | Crea task schedulato per download automatico |
| `run.bat` | Esegue il download delle note da Gmail |
