@echo off
setlocal

cd /d "%~dp0"
title StorySpeech AI Runner

echo.
echo ================================================
echo  Multilingual Story Generation ^& Speech System
echo ================================================
echo.

set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python was not found. Please install Python 3.10 or later.
        echo Download: https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py -3"
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto error
)

echo Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

echo Installing required packages...
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install -r requirements.txt
if errorlevel 1 goto error

if not exist ".env" (
    echo Creating .env from .env.example...
    copy ".env.example" ".env" >nul
    echo You can add your GEMINI_API_KEY inside the new .env file.
)

echo.
echo Starting Flask server...
echo Open this URL if the browser does not open automatically:
echo http://127.0.0.1:5000
echo.
start "" "http://127.0.0.1:5000"
python app.py
goto end

:error
echo.
echo Setup failed. Please check the error message above.
pause
exit /b 1

:end
echo.
echo Server stopped.
pause
