@echo off
:: ============================================================
:: SETUP OBSIDIAN - Prepara il vault MeetWiki con i plugin
:: Tutta la logica e' in scripts\setup_obsidian.ps1
:: Uso: setup_obsidian.bat [-Force]
:: ============================================================
setlocal
set ROOT=%~dp0..\
cd /d "%ROOT%"

echo.
echo ============================================================
echo  MeetWiki - Setup Vault Obsidian
echo ============================================================
echo.

:: 1. Struttura vault base
echo [1/2] Creazione struttura vault...
if not exist "MeetWiki\.obsidian"           mkdir "MeetWiki\.obsidian"
if not exist "MeetWiki\.obsidian\plugins"   mkdir "MeetWiki\.obsidian\plugins"
if not exist "MeetWiki\notes"               mkdir "MeetWiki\notes"
if not exist "MeetWiki\topics"              mkdir "MeetWiki\topics"
if not exist "MeetWiki\people"              mkdir "MeetWiki\people"
if not exist "MeetWiki\digests"             mkdir "MeetWiki\digests"
if not exist "MeetWiki\actions"             mkdir "MeetWiki\actions"
if not exist "MeetWiki\actions\by-owner"    mkdir "MeetWiki\actions\by-owner"
if not exist "MeetWiki\actions\kanban"      mkdir "MeetWiki\actions\kanban"
if not exist "MeetWiki\.meta"               mkdir "MeetWiki\.meta"
echo       Struttura vault OK.

:: 2. Download/update plugin via PowerShell helper
echo [2/2] Download plugin community...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_obsidian.ps1" %*
if errorlevel 1 (
    echo.
    echo ERRORE: il setup dei plugin ha incontrato problemi.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup Obsidian completato!
echo ============================================================
echo.
echo PER ATTIVARE in Obsidian:
echo   1. Apri Obsidian -^> Open folder as vault -^> MeetWiki\
echo   2. Settings -^> Community plugins -^> Turn on community plugins
echo   3. I plugin attivi sono elencati in
echo      MeetWiki\.obsidian\community-plugins.json
echo.
echo NOTA: NON serve scaricare nulla da Obsidian, i plugin sono gia' a disco.
echo Per aggiornare i plugin: setup_obsidian.bat -Force
echo ============================================================
pause
