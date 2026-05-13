@echo off
setlocal

if "%~4"=="" (
  echo Usage: run.bat RUN_DIR REGION DELAY CATEGORY [NODE_DIR]
  exit /b 1
)

set "RUN_DIR=%~1"
set "REGION=%~2"
set "DELAY=%~3"
set "CATEGORY=%~4"

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=D:\_soft\Anaconda\envs\WQBRAIN\python.exe"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "ROOT_DIR=%%~fI"
set "NODE_TMP=%TEMP%\codex_node_dir_E.txt"

if "%~5"=="" (
  "%PYTHON_EXE%" "%ROOT_DIR%\workflow\shared\resolve_node_dir.py" "%RUN_DIR%" "E_data_and_field_feasibility" create > "%NODE_TMP%"
  set /p NODE_DIR=<"%NODE_TMP%"
) else (
  set "NODE_DIR=%~5"
)
if "%NODE_DIR%"=="STEP_LIMIT_EXCEEDED" exit /b 99

if not exist "%NODE_DIR%" mkdir "%NODE_DIR%"

"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\fetch_active_alphas.py" "%NODE_DIR%" "%REGION%" "%DELAY%" "%CATEGORY%"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\extract_used_fields.py" "%NODE_DIR%" "%REGION%" "%DELAY%" "%CATEGORY%"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\screen_datasets.py" "%NODE_DIR%" "%REGION%" "%DELAY%" "%CATEGORY%"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\build_available_datafields.py" "%NODE_DIR%" "%REGION%" "%DELAY%" "%CATEGORY%"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\write_summary.py" "%NODE_DIR%" "%REGION%" "%DELAY%" "%CATEGORY%"
if errorlevel 1 exit /b 1

echo Node completed: data_and_field_feasibility
echo Output directory: %NODE_DIR%

if exist "%NODE_TMP%" del "%NODE_TMP%"
endlocal
