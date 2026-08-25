@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
)

echo Fetching latest data and building report...
"%PY%" fetch_data.py
if errorlevel 1 goto :error
"%PY%" build_report.py
if errorlevel 1 goto :error
start "" "report.html"
goto :eof

:error
echo.
echo Something went wrong - see the error above.
pause
