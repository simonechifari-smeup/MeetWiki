@echo off
:: ============================================================
:: Installa il downloader Gemini come attivita' pianificata Windows
:: Esegue lo script ogni 10 minuti in background
:: ESEGUIRE COME AMMINISTRATORE
:: ============================================================
set TASK_NAME=GeminiNotesDownloader
set PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe
set SCRIPT_PATH=%~dp0gemini_notes_downloader.py

echo Registrazione attivita' pianificata: %TASK_NAME%
echo Intervallo: ogni 10 minuti

schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON_EXE%\" \"%SCRIPT_PATH%\"" ^
  /sc minute ^
  /mo 10 ^
  /ru "%USERNAME%" ^
  /f

if errorlevel 1 (
    echo ERRORE: esegui questo script come Amministratore.
) else (
    echo.
    echo Attivita' pianificata creata con successo!
    echo Puoi gestirla dal Utilita' di pianificazione di Windows.
    echo.
    echo Per rimuoverla:  schtasks /delete /tn "%TASK_NAME%" /f
)
pause
