@echo off
setlocal enabledelayedexpansion
title rag-kit Installer (Windows)

echo ============================================================
echo   rag-kit Installer - Windows
echo   Agentic RAG System for Hermes Agent
echo ============================================================
echo.

set "INSTALL_DIR=%USERPROFILE%\rag-kit-venv"
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM ---- Step 1: Check Python >= 3.10 ----
echo [1/7] Checking Python...

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Python not found in PATH. Please install Python 3.10+ first.
    echo   Download: https://www.python.org/downloads/
    goto :end_fail
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo   Found Python %PY_VER%

for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

if !PY_MAJOR! LSS 3 (
    echo   ERROR: Python 3.10+ required, found %PY_VER%
    goto :end_fail
)
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 10 (
    echo   ERROR: Python 3.10+ required, found %PY_VER%
    goto :end_fail
)
echo   OK: Python %PY_VER% meets requirements
echo.

REM ---- Step 2: Detect GPU ----
echo [2/7] Detecting GPU...

set "USE_CUDA=0"
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    nvidia-smi >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "USE_CUDA=1"
        for /f "tokens=*" %%g in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do set "GPU_NAME=%%g"
        echo   GPU detected: !GPU_NAME!
        echo   Will install PyTorch with CUDA support.
    ) else (
        echo   nvidia-smi found but GPU not available. Using CPU mode.
    )
) else (
    echo   No NVIDIA GPU detected. Using CPU mode.
)
echo.

REM ---- Step 3: Create virtual environment ----
echo [3/7] Creating virtual environment at !INSTALL_DIR!...

if exist "!INSTALL_DIR!" (
    echo   Removing existing installation...
    rmdir /s /q "!INSTALL_DIR!" 2>nul
)

python -m venv "!INSTALL_DIR!"
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Failed to create virtual environment.
    goto :end_fail
)
echo   Created: !INSTALL_DIR!
echo.

REM ---- Step 4: Install dependencies ----
echo [4/7] Installing dependencies...

call "!INSTALL_DIR!\Scripts\activate.bat" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Failed to activate virtual environment.
    goto :end_fail
)

REM Upgrade pip first
python -m pip install --upgrade pip --quiet 2>nul

if !USE_CUDA! EQU 1 (
    echo   Installing PyTorch with CUDA...
    python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet
    if !ERRORLEVEL! NEQ 0 (
        echo   WARNING: CUDA PyTorch failed. Falling back to CPU PyTorch...
        python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
    )
) else (
    echo   Installing PyTorch (CPU)...
    python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
)

if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Failed to install PyTorch.
    goto :end_fail
)

echo   Installing rag-kit and dependencies...
cd /d "%PROJECT_DIR%"
python -m pip install -e ".[ocr]" --quiet

if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Failed to install rag-kit.
    goto :end_fail
)
echo   Installation complete.
echo.

REM ---- Step 5: Verify imports and CLI ----
echo [5/7] Verifying installation...

REM Test imports
python -c "import rag_kit; print('  rag_kit v' + rag_kit.__version__)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   ERROR: Failed to import rag_kit.
    goto :end_fail
)

python -c "import rag_kit.autostart; print('  autostart OK')" 2>nul
python -c "import rag_kit.watcher; print('  watcher OK')" 2>nul

REM Test CLI
rag --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   CLI: rag --version OK
) else (
    echo   WARNING: rag CLI not found in PATH.
    echo   You can run it from: !INSTALL_DIR!\Scripts\rag.exe
)

REM Create default config
rag config init >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   Config: Created default config
) else (
    echo   WARNING: Could not create default config (non-fatal)
)

REM Create default watch folder
if not exist "%USERPROFILE%\Documents\rag-ingest" (
    mkdir "%USERPROFILE%\Documents\rag-ingest" 2>nul
    if !ERRORLEVEL! EQU 0 echo   Created watch folder: %USERPROFILE%\Documents\rag-ingest
)
echo   Verification passed.
echo.

REM ---- Step 6: Setup autostart ----
echo [6/7] Setting up autostart...

rag setup-autostart --interval 30 --json 2>nul
if %ERRORLEVEL% EQU 0 (
    echo   Autostart: Installed (rag-kit-watcher will start on logon)
) else (
    echo   Autostart: NOT installed ^(admin rights required for schtasks^)
    echo   To install autostart manually, run as Administrator:
    echo     "!INSTALL_DIR!\Scripts\rag.exe" setup-autostart
)
echo.

REM ---- Step 7: Start watcher daemon ----
echo [7/7] Starting watcher daemon...

REM Use pythonw to run without a console window
start /B pythonw -m rag_kit.watcher >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   Watcher: Running (background daemon)
    echo   Watch folder: %USERPROFILE%\Documents\rag-ingest
) else (
    echo   Watcher: Could not start. Run manually:
    echo     "!INSTALL_DIR!\Scripts\rag.exe" watch "%USERPROFILE%\Documents\rag-ingest"
)
echo.

REM ---- Copy Hermes Agent skill ----
set "SKILL_SRC=%PROJECT_DIR%\SKILL.md"
set "SKILL_DST=%USERPROFILE%\AppData\Local\hermes\skills\research\rag-kit\SKILL.md"

if exist "%SKILL_SRC%" (
    if not exist "%SKILL_DST%" (
        mkdir "%USERPROFILE%\AppData\Local\hermes\skills\research\rag-kit" 2>nul >nul
        copy "%SKILL_SRC%" "%SKILL_DST%" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo Hermes Agent skill installed: research/rag-kit
        )
    )
)

REM ---- Summary ----
echo ============================================================
echo   Installation Complete
echo ============================================================
echo.

REM Check autostart status
rag setup-autostart --json 2>nul | findstr /c:"installed" >nul
if %ERRORLEVEL% EQU 0 (
    echo   Autostart:    Installed ^(on logon^)
) else (
    echo   Autostart:    NOT installed ^(run as Admin to install^)
)

REM Check if watcher is running
tasklist /fi "imagename eq pythonw.exe" 2>nul | findstr /c:"pythonw" >nul
if %ERRORLEVEL% EQU 0 (
    echo   Watcher:      Running
) else (
    echo   Watcher:      Not running ^(start manually^)
)

echo.
echo   Installation directory: !INSTALL_DIR!
echo   CLI executable:        !INSTALL_DIR!\Scripts\rag.exe
echo   Config file:           %USERPROFILE%\.rag-kit.yaml
echo   Watch folder:          %USERPROFILE%\Documents\rag-ingest
echo   Vector DB:             %USERPROFILE%\lancedb
echo   Model cache:           %USERPROFILE%\models
echo.
echo   Quick start:
echo     Drop documents in: %USERPROFILE%\Documents\rag-ingest
echo     Then query:        rag query --json "your question"
echo     Check status:      rag status
echo.
echo   For help: rag --help
echo.

pause
exit /b 0

:end_fail
echo.
echo ============================================================
echo   Installation FAILED
echo ============================================================
echo   Please check the errors above and try again.
echo   For help: https://github.com/jarvi/rag-kit
echo.
pause
exit /b 1