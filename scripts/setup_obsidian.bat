@echo off
:: ============================================================
:: SETUP OBSIDIAN - Prepara il vault MeetWiki con i plugin
:: Scarica/aggiorna i plugin community da GitHub Releases
:: ============================================================
setlocal enabledelayedexpansion
set ROOT=%~dp0..\
cd /d "%ROOT%"

echo.
echo ============================================================
echo  MeetWiki - Setup Vault Obsidian
echo ============================================================
echo.

set PLUGINS_DIR=MeetWiki\.obsidian\plugins

:: --------------------------------------------------
:: 1. Struttura vault base
:: --------------------------------------------------
echo [1/4] Creazione struttura vault...
if not exist "MeetWiki\.obsidian" mkdir "MeetWiki\.obsidian"
if not exist "%PLUGINS_DIR%" mkdir "%PLUGINS_DIR%"
if not exist "MeetWiki\notes" mkdir "MeetWiki\notes"
if not exist "MeetWiki\topics" mkdir "MeetWiki\topics"
if not exist "MeetWiki\people" mkdir "MeetWiki\people"
if not exist "MeetWiki\digests" mkdir "MeetWiki\digests"
if not exist "MeetWiki\actions" mkdir "MeetWiki\actions"
if not exist "MeetWiki\actions\by-owner" mkdir "MeetWiki\actions\by-owner"
if not exist "MeetWiki\actions\kanban" mkdir "MeetWiki\actions\kanban"
if not exist "MeetWiki\.meta" mkdir "MeetWiki\.meta"
echo       Struttura vault OK.

:: --------------------------------------------------
:: 2. community-plugins.json
:: --------------------------------------------------
echo [2/4] Configurazione plugin list...
if not exist "MeetWiki\.obsidian\community-plugins.json" (
    echo ["dataview","obsidian-kanban","copilot"]> "MeetWiki\.obsidian\community-plugins.json"
    echo       community-plugins.json creato.
) else (
    echo       community-plugins.json gia' presente.
)

:: --------------------------------------------------
:: 3. Download plugin Kanban
:: --------------------------------------------------
echo [3/4] Plugin obsidian-kanban...
set KANBAN_DIR=%PLUGINS_DIR%\obsidian-kanban
if not exist "%KANBAN_DIR%" mkdir "%KANBAN_DIR%"

if exist "%KANBAN_DIR%\main.js" (
    echo       Kanban gia' installato. Per aggiornare, elimina %KANBAN_DIR% e riesegui.
) else (
    echo       Download obsidian-kanban da GitHub...
    powershell -NoProfile -Command ^
        "$rel = Invoke-RestMethod 'https://api.github.com/repos/mgmeyers/obsidian-kanban/releases/latest' -Headers @{'User-Agent'='meetwiki'}; " ^
        "foreach ($n in 'main.js','manifest.json','styles.css') { " ^
        "  $a = $rel.assets | Where-Object name -eq $n | Select-Object -First 1; " ^
        "  if ($a) { Invoke-WebRequest -Uri $a.browser_download_url -OutFile '%KANBAN_DIR%\' + $n -UseBasicParsing } " ^
        "}"
    if exist "%KANBAN_DIR%\main.js" (
        echo       Kanban installato con successo.
    ) else (
        echo       ERRORE: download Kanban fallito. Verifica connessione internet.
    )
)

:: --------------------------------------------------
:: 4. Download plugin Dataview
:: --------------------------------------------------
echo [4/4] Plugin dataview...
set DATAVIEW_DIR=%PLUGINS_DIR%\dataview
if not exist "%DATAVIEW_DIR%" mkdir "%DATAVIEW_DIR%"

if exist "%DATAVIEW_DIR%\main.js" (
    echo       Dataview gia' installato. Per aggiornare, elimina %DATAVIEW_DIR% e riesegui.
) else (
    echo       Download dataview da GitHub...
    powershell -NoProfile -Command ^
        "$rel = Invoke-RestMethod 'https://api.github.com/repos/blacksmithgu/obsidian-dataview/releases/latest' -Headers @{'User-Agent'='meetwiki'}; " ^
        "foreach ($n in 'main.js','manifest.json','styles.css') { " ^
        "  $a = $rel.assets | Where-Object name -eq $n | Select-Object -First 1; " ^
        "  if ($a) { Invoke-WebRequest -Uri $a.browser_download_url -OutFile '%DATAVIEW_DIR%\' + $n -UseBasicParsing } " ^
        "}"
    if exist "%DATAVIEW_DIR%\main.js" (
        echo       Dataview installato con successo.
    ) else (
        echo       ERRORE: download Dataview fallito. Verifica connessione internet.
    )
)

:: --------------------------------------------------
:: Riepilogo
:: --------------------------------------------------
echo.
echo ============================================================
echo  Setup Obsidian completato!
echo ============================================================
echo.
echo Plugin installati in: %PLUGINS_DIR%\
echo.
echo PER ATTIVARE:
echo   1. Apri Obsidian -^> Open folder as vault -^> MeetWiki\
echo   2. Settings -^> Community plugins -^> Turn on community plugins
echo   3. Verifica che Kanban e Dataview siano attivi (toggle verde)
echo.
echo NOTA: NON serve scaricare nulla da Obsidian, i plugin sono gia' a disco.
echo ============================================================
pause
