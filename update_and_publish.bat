@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
)

echo [%date% %time%] Fetching latest data and building report... >> update_log.txt
"%PY%" fetch_data.py >> update_log.txt 2>&1
if errorlevel 1 goto :error
"%PY%" build_report.py >> update_log.txt 2>&1
if errorlevel 1 goto :error

git add data\lotto_raw.csv data\picks_history.json report.html >> update_log.txt 2>&1
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "עדכון אוטומטי: נתוני הגרלות + דוח" >> update_log.txt 2>&1
    git push origin master >> update_log.txt 2>&1
    echo [%date% %time%] Pushed update. >> update_log.txt
) else (
    echo [%date% %time%] No changes to push. >> update_log.txt
)
goto :eof

:error
echo [%date% %time%] ERROR during update - see above. >> update_log.txt
