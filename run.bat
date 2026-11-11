@echo off
rem Double-click this file to run the backtest with the project's own Python environment.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Setting up the Python environment, this happens only once...
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :error
)
".venv\Scripts\python.exe" run.py %* || goto :error
echo.
echo Done. Opening the interactive chart in your browser...
start "" "%~dp0results\interactive_chart.html"
pause
exit /b 0

:error
echo.
echo Something went wrong, see the message above.
pause
exit /b 1
