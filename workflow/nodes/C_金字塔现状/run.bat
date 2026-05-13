@echo off
setlocal

if "%~1"=="" (
  echo Usage: run.bat RUN_DIR [QUARTER] [YEAR] [NODE_DIR]
  exit /b 1
)

set "RUN_DIR=%~1"
set "QUARTER=%~2"
set "YEAR=%~3"

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "ROOT_DIR=%%~fI"
set "PYTHON_EXE=D:\_soft\Anaconda\envs\WQBRAIN\python.exe"
set "NODE_TMP=%TEMP%\codex_node_dir_C.txt"

if "%~4"=="" (
  "%PYTHON_EXE%" "%ROOT_DIR%\workflow\shared\resolve_node_dir.py" "%RUN_DIR%" "C_pyramid_status" create > "%NODE_TMP%"
  set /p NODE_DIR=<"%NODE_TMP%"
) else (
  set "NODE_DIR=%~4"
)
if "%NODE_DIR%"=="STEP_LIMIT_EXCEEDED" exit /b 99

if not exist "%NODE_DIR%" mkdir "%NODE_DIR%"

if "%QUARTER%"=="" (
  "%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_pyramid_alphas.py" --scope quarter > "%NODE_DIR%\current_quarter_pyramids.json"
) else (
  if "%YEAR%"=="" (
    "%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_pyramid_alphas.py" --quarter %QUARTER% > "%NODE_DIR%\current_quarter_pyramids.json"
  ) else (
    "%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_pyramid_alphas.py" --quarter %QUARTER% --year %YEAR% > "%NODE_DIR%\current_quarter_pyramids.json"
  )
)
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_pyramid_alphas.py" --scope all > "%NODE_DIR%\all_pyramids.json"
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" "%ROOT_DIR%\wqb_core\user\get_pyramid_multipliers.py" > "%NODE_DIR%\multipliers.json"
if errorlevel 1 exit /b 1

> "%NODE_DIR%\node_summary.md" echo # Pyramid Status
>> "%NODE_DIR%\node_summary.md" echo.
>> "%NODE_DIR%\node_summary.md" echo ## Outputs
>> "%NODE_DIR%\node_summary.md" echo - current_quarter_pyramids.json
>> "%NODE_DIR%\node_summary.md" echo - all_pyramids.json
>> "%NODE_DIR%\node_summary.md" echo - multipliers.json

echo Node completed: pyramid_status
echo Output directory: %NODE_DIR%

if exist "%NODE_TMP%" del "%NODE_TMP%"
endlocal
