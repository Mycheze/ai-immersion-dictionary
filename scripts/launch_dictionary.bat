@echo off
REM DeepDict launcher script for Windows

REM Get the script's directory
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%\.."

REM Convert to absolute path
pushd "%ROOT_DIR%"
set "ROOT_DIR=%CD%"
popd

REM Check if virtual environment exists
set "VENV_DIR=%ROOT_DIR%\venv"
if exist "%VENV_DIR%" (
    echo Using virtual environment at %VENV_DIR%
    
    REM Activate virtual environment
    if exist "%VENV_DIR%\Scripts\activate.bat" (
        call "%VENV_DIR%\Scripts\activate.bat"
    ) else (
        echo Error: Virtual environment activation script not found.
        echo Try reinstalling with: python -m venv venv
        exit /b 1
    )
) else (
    echo Warning: Virtual environment not found at %VENV_DIR%
    echo Running with system Python (dependencies may be missing)
)

REM Ensure data directory exists
if not exist "%ROOT_DIR%\data" (
    mkdir "%ROOT_DIR%\data"
)

REM Check if API key exists
if not exist "%ROOT_DIR%\api_key.txt" (
    echo API key not found. Running setup script...
    python "%ROOT_DIR%\setup.py"
)

REM Launch the application
echo Launching DeepDict...
python "%ROOT_DIR%\src\app.py"

REM Deactivate virtual environment (if we activated it)
if defined VIRTUAL_ENV (
    call deactivate
)