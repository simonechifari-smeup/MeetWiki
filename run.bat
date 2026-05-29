@echo off
:: ============================================================
:: RUN - Scarica le note Gemini da Gmail
:: ============================================================
cd /d "%~dp0"

:: Controlla se Chrome e' gia' aperto con la porta di debug.
:: Se no, aprilo ora (e lascialo aperto anche dopo lo script).
curl -s http://localhost:9222/json/version >nul 2>&1
if errorlevel 1 (
    echo Avvio Chrome con porta debug remoto...
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --no-first-run --no-default-browser-check
    timeout /t 3 /nobreak >nul
)

"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\gemini_notes_downloader.py"
if errorlevel 1 (
    echo.
    echo ERRORE durante l'esecuzione. Controlla downloader.log per dettagli.
    pause
)
