@echo off
setlocal

if "%~1"=="" (
  echo Usage: run.bat RUN_DIR [NODE_DIR]
  exit /b 1
)

set "RUN_DIR=%~1"
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "ROOT_DIR=%%~fI"
set "PYTHON_EXE=D:\_soft\Anaconda\envs\WQBRAIN\python.exe"
set "NODE_TMP=%TEMP%\codex_node_dir_A.txt"

if "%~2"=="" (
  "%PYTHON_EXE%" "%ROOT_DIR%\workflow\shared\resolve_node_dir.py" "%RUN_DIR%" "A_login_shared_auth" create > "%NODE_TMP%"
  set /p NODE_DIR=<"%NODE_TMP%"
) else (
  set "NODE_DIR=%~2"
)
if "%NODE_DIR%"=="STEP_LIMIT_EXCEEDED" exit /b 99

if not exist "%NODE_DIR%" mkdir "%NODE_DIR%"

"%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\post_authentication.py" > "%NODE_DIR%\post_authentication.json"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_authentication.py" > "%NODE_DIR%\get_authentication.json"
if errorlevel 1 exit /b 1

> "%NODE_DIR%\node_summary.md" echo # Login and Shared Auth
>> "%NODE_DIR%\node_summary.md" echo.
>> "%NODE_DIR%\node_summary.md" echo ## Commands
>> "%NODE_DIR%\node_summary.md" echo - "%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\post_authentication.py"
>> "%NODE_DIR%\node_summary.md" echo - "%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_authentication.py"
>> "%NODE_DIR%\node_summary.md" echo.
>> "%NODE_DIR%\node_summary.md" echo ## Outputs
>> "%NODE_DIR%\node_summary.md" echo - post_authentication.json
>> "%NODE_DIR%\node_summary.md" echo - get_authentication.json

echo Node completed: login_and_shared_auth
echo Output directory: %NODE_DIR%

if exist "%NODE_TMP%" del "%NODE_TMP%"
endlocal
