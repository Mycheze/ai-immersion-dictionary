@echo off
REM Root launcher script that calls the more comprehensive launch script in scripts directory

REM Get the script's directory
set "SCRIPT_DIR=%~dp0"

REM Call the main launcher script
"%SCRIPT_DIR%scripts\launch_dictionary.bat" %*