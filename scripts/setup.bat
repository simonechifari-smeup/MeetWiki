@echo off
:: ============================================================
:: SETUP - Da eseguire UNA SOLA VOLTA
:: ============================================================
set ROOT=%~dp0..\
echo Installazione dipendenze Python...
pip install -r "%ROOT%requirements.txt"
if errorlevel 1 (
    echo ERRORE: pip non trovato. Assicurati che Python sia installato e nel PATH.
    pause
    exit /b 1
)

echo Installazione browser Playwright...
playwright install chromium
if errorlevel 1 (
    echo ERRORE durante installazione browser Playwright.
    pause
    exit /b 1
)

echo.
echo Creazione file .env di configurazione...
if not exist "%ROOT%.env" (
    echo OUTPUT_DIR=%ROOT%note_riunioni> "%ROOT%.env"
    echo File .env creato. Modifica OUTPUT_DIR se vuoi cambiare la cartella di destinazione.
) else (
    echo File .env gia' esistente, non sovrascritto.
)

echo.
echo ============================================================
echo Setup completato!
echo.
echo PROSSIMO PASSO:
echo   1. Chiudi Google Chrome completamente
echo   2. Esegui run.bat (dalla root del progetto)
echo   3. Si aprira' Chrome automaticamente con il tuo account gia' loggato
echo   4. Lo script scarichera' le note Gemini in Markdown
echo.
echo Per esecuzione automatica ogni 10 minuti:
echo   Esegui scripts\schedule_task.bat come Amministratore
echo ============================================================
pause

