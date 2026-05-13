@echo off
setlocal

if "%~1"=="" (
  echo Usage: run.bat RUN_DIR [MESSAGES_SUMMARY_LIMIT] [MESSAGES_FULL_LIMIT] [MESSAGES_OFFSET] [NODE_DIR]
  exit /b 1
)

set "RUN_DIR=%~1"
set "MESSAGES_SUMMARY_LIMIT=%~2"
set "MESSAGES_FULL_LIMIT=%~3"
set "MESSAGES_OFFSET=%~4"

if "%MESSAGES_SUMMARY_LIMIT%"=="" set "MESSAGES_SUMMARY_LIMIT=20"
if "%MESSAGES_FULL_LIMIT%"=="" set "MESSAGES_FULL_LIMIT=50"
if "%MESSAGES_OFFSET%"=="" set "MESSAGES_OFFSET=0"

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "ROOT_DIR=%%~fI"
set "PYTHON_EXE=D:\_soft\Anaconda\envs\WQBRAIN\python.exe"
set "NODE_TMP=%TEMP%\codex_node_dir_B.txt"

if "%~5"=="" (
  "%PYTHON_EXE%" "%ROOT_DIR%\workflow\shared\resolve_node_dir.py" "%RUN_DIR%" "B_theme_platform_opportunities" create > "%NODE_TMP%"
  set /p NODE_DIR=<"%NODE_TMP%"
) else (
  set "NODE_DIR=%~5"
)
if "%NODE_DIR%"=="STEP_LIMIT_EXCEEDED" exit /b 99

if not exist "%NODE_DIR%" mkdir "%NODE_DIR%"

"%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_messages_summary.py" --limit %MESSAGES_SUMMARY_LIMIT% > "%NODE_DIR%\messages_summary.json"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_messages.py" --limit %MESSAGES_FULL_LIMIT% --offset %MESSAGES_OFFSET% > "%NODE_DIR%\messages_full.json"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\community\get_events.py" > "%NODE_DIR%\events.json"
if errorlevel 1 exit /b 1

> "%NODE_DIR%\node_summary.md" echo # Theme and Platform Opportunities
>> "%NODE_DIR%\node_summary.md" echo.
>> "%NODE_DIR%\node_summary.md" echo ## Outputs
>> "%NODE_DIR%\node_summary.md" echo - messages_summary.json
>> "%NODE_DIR%\node_summary.md" echo - messages_full.json
>> "%NODE_DIR%\node_summary.md" echo - events.json

echo Node completed: theme_and_platform_opportunities
echo Output directory: %NODE_DIR%

if exist "%NODE_TMP%" del "%NODE_TMP%"
endlocal
