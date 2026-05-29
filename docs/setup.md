# ⚙️ Setup

## Prerequisiti

- **Windows 10/11**
- **Python 3.12+** (testato con 3.14)
- **Google Chrome** installato e loggato con il tuo account Google
- **Git** (opzionale, per versionamento)

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

Questo script:
- Crea l'ambiente virtuale `.venv/`
- Installa le dipendenze da `requirements.txt`
- Installa i browser Playwright

### 3. Configura il file `.env`

```powershell
cp .env.example .env
```

Modifica `.env` con i tuoi valori:

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `OUTPUT_DIR` | Percorso cartella dove salvare le note scaricate | `./note_riunioni` |
| `MEETWIKI_OWNER` | Il tuo nome per la board Kanban personale | (auto-detect) |
| `CHROME_USER_DATA` | Percorso User Data di Chrome | `%LOCALAPPDATA%\Google\Chrome\User Data` |
| `CHROME_PROFILE` | Profilo Chrome da utilizzare | `Default` |
| `CHROME_EXE` | Percorso eseguibile Chrome | `C:\Program Files\Google\Chrome\Application\chrome.exe` |
| `GITHUB_MODELS_TOKEN` | Token GitHub per Obsidian Copilot (opzionale) | — |

### 4. Verifica

```powershell
.venv\Scripts\python.exe -c "from playwright.sync_api import sync_playwright; print('OK')"
```

## Schedulazione automatica (opzionale)

Per scaricare le note in automatico ogni giorno:

```powershell
scripts\schedule_task.bat
```

Crea un task di Windows Task Scheduler che esegue `run.bat` all'orario configurato.

## Obsidian (opzionale)

1. Apri Obsidian → *Open folder as vault* → seleziona `MeetWiki/`
2. Settings → Community plugins → **Turn on community plugins**
3. I plugin (`obsidian-kanban`, `dataview`) sono già inclusi e pre-configurati

Vedi [MeetWiki/README.md](../MeetWiki/README.md#obsidian-setup-e-uso) per dettagli.
