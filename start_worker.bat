@echo off
setlocal
cd /d "%~dp0"
if exist "config\runtime.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("config\runtime.env") do if not "%%A"=="" set "%%A=%%B"
)
if not exist ".venv\Scripts\opai.exe" (
  echo Local virtualenv is missing. Create .venv with Python 3.11+ and run: .venv\Scripts\pip install -e app pytest
  exit /b 1
)
if "%OPAI_HEROSMS_API_KEY%%OPAI_HEROSMS_API_KEY_FILE%"=="" (
  echo Missing Hero-SMS API key. Set OPAI_HEROSMS_API_KEY or OPAI_HEROSMS_API_KEY_FILE in config\runtime.env.
  exit /b 1
)
".venv\Scripts\opai.exe" worker run %*
