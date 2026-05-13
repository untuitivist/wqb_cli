@echo off
setlocal

if "%~4"=="" (
  echo Usage: run.bat RUN_ROOT REGION DELAY CATEGORY [NODE_DIR]
  exit /b 1
)

set "RUN_ROOT=%~1"
set "REGION=%~2"
set "DELAY=%~3"
set "CATEGORY=%~4"
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "ROOT_DIR=%%~fI"
set "PYTHON_EXE=D:\_soft\Anaconda\envs\WQBRAIN\python.exe"
set "NODE_TMP=%TEMP%\codex_node_dir_K.txt"

if "%~5"=="" (
  "%PYTHON_EXE%" "%ROOT_DIR%\workflow\shared\resolve_node_dir.py" "%RUN_ROOT%" "K_diagnosis" create > "%NODE_TMP%"
  set /p NODE_DIR=<"%NODE_TMP%"
) else (
  set "NODE_DIR=%~5"
)
if "%NODE_DIR%"=="STEP_LIMIT_EXCEEDED" exit /b 99

if not exist "%NODE_DIR%" mkdir "%NODE_DIR%"

"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\fetch_alpha_details.py" "%RUN_ROOT%" "%NODE_DIR%" "%REGION%" "%DELAY%" "%CATEGORY%"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\build_diagnosis.py" "%NODE_DIR%" "%REGION%" "%DELAY%" "%CATEGORY%"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%SCRIPT_DIR%scripts\write_summary.py" "%NODE_DIR%" "%REGION%" "%DELAY%" "%CATEGORY%"
if errorlevel 1 exit /b 1

set "NEXT_NODE_TMP=%TEMP%\codex_next_node_K.txt"
"%PYTHON_EXE%" "%ROOT_DIR%\workflow\shared\read_diagnosis_next_node.py" "%NODE_DIR%\diagnosis__%REGION%_D%DELAY%_%CATEGORY%.json" > "%NEXT_NODE_TMP%"
set /p NEXT_NODE=<"%NEXT_NODE_TMP%"

if /I "%NEXT_NODE%"=="BEST_K_BRANCH" (
  "%PYTHON_EXE%" "%ROOT_DIR%\workflow\shared\archive_to_best_k_error_branch.py" "%RUN_ROOT%" "%NODE_DIR%"
  if errorlevel 1 exit /b 1
  echo Node completed: diagnosis
  echo Decision: BEST_K_BRANCH
  if exist "%NEXT_NODE_TMP%" del "%NEXT_NODE_TMP%"
  if exist "%NODE_TMP%" del "%NODE_TMP%"
  endlocal
  exit /b 0
)

echo Node completed: diagnosis
echo Output directory: %NODE_DIR%

if exist "%NEXT_NODE_TMP%" del "%NEXT_NODE_TMP%"
if exist "%NODE_TMP%" del "%NODE_TMP%"
endlocal
