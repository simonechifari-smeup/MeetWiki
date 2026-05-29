@echo off
:: ============================================================
:: SETUP - Da eseguire UNA SOLA VOLTA dopo il clone
:: Crea venv, installa dipendenze, prepara vault Obsidian
:: ============================================================
setlocal enabledelayedexpansion
set ROOT=%~dp0..\
cd /d "%ROOT%"

echo.
echo ============================================================
echo  MeetWiki - Setup iniziale
echo ============================================================
echo.

:: --------------------------------------------------
:: 1. Creazione ambiente virtuale Python
:: --------------------------------------------------
echo [1/5] Creazione ambiente virtuale .venv...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 (
        echo ERRORE: Python non trovato. Assicurati che Python 3.12+ sia installato e nel PATH.
        pause
        exit /b 1
    )
    echo       .venv creato.
) else (
    echo       .venv gia' esistente, skip.
)

:: --------------------------------------------------
:: 2. Installazione dipendenze
:: --------------------------------------------------
echo [2/5] Installazione dipendenze Python...
.venv\Scripts\pip.exe install --upgrade pip -q
.venv\Scripts\pip.exe install -r requirements.txt -q
if errorlevel 1 (
    echo ERRORE: installazione dipendenze fallita.
    pause
    exit /b 1
)
echo       Dipendenze installate.

:: --------------------------------------------------
:: 3. Installazione browser Playwright
:: --------------------------------------------------
echo [3/5] Installazione browser Playwright (chromium)...
.venv\Scripts\playwright.exe install chromium
if errorlevel 1 (
    echo ERRORE durante installazione browser Playwright.
    pause
    exit /b 1
)
echo       Chromium installato.

:: --------------------------------------------------
:: 4. Creazione file .env
:: --------------------------------------------------
echo [4/5] Configurazione .env...
if not exist ".env" (
    copy ".env.example" ".env" >nul 2>&1
    if not exist ".env" (
        echo OUTPUT_DIR=%ROOT%note_riunioni> ".env"
    )
    echo       .env creato da .env.example. Modificalo con i tuoi valori.
) else (
    echo       .env gia' esistente, non sovrascritto.
)

:: --------------------------------------------------
:: 5. Creazione cartelle necessarie
:: --------------------------------------------------
echo [5/5] Creazione struttura cartelle...
if not exist "note_riunioni" mkdir "note_riunioni"
if not exist "note_riunioni\archive" mkdir "note_riunioni\archive"
if not exist ".cache" mkdir ".cache"
if not exist "MeetWiki\notes" mkdir "MeetWiki\notes"
if not exist "MeetWiki\.meta" mkdir "MeetWiki\.meta"
echo       Cartelle create.

:: --------------------------------------------------
:: Verifica vault Obsidian
:: --------------------------------------------------
echo.
echo Verifica vault Obsidian...
if exist "MeetWiki\.obsidian\plugins\obsidian-kanban\main.js" (
    echo       Plugin Kanban: OK
) else (
    echo       ATTENZIONE: Plugin Kanban mancante. Esegui scripts\setup_obsidian.bat
)
if exist "MeetWiki\.obsidian\plugins\dataview\main.js" (
    echo       Plugin Dataview: OK
) else (
    echo       ATTENZIONE: Plugin Dataview mancante. Esegui scripts\setup_obsidian.bat
)

echo.
echo ============================================================
echo  Setup completato!
echo ============================================================
echo.
echo PROSSIMI PASSI:
echo   1. Modifica .env con i tuoi valori (OUTPUT_DIR, MEETWIKI_OWNER)
echo   2. Chiudi Google Chrome completamente
echo   3. Esegui menu.cmd per scaricare le note da Gmail
echo   4. Esegui: .venv\Scripts\python.exe scripts\meetwiki_update.py
echo.
echo OPZIONALE:
echo   - Apri MeetWiki/ in Obsidian per le board Kanban
echo   - Esegui scripts\schedule_task.bat per schedulazione automatica
echo ============================================================
pause

