@echo off
setlocal enabledelayedexpansion
title rag-kit Model Downloader (Windows)

echo ============================================================
echo   rag-kit - Model Downloader
echo   Downloads all models for offline use
echo ============================================================
echo.
echo This script pre-downloads models to %%USERPROFILE%%\models\
echo so rag-kit can work fully offline after installation.
echo.
set "MODEL_DIR=%USERPROFILE%\models"

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.10+ first.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if huggingface_hub is installed; if not, install it
python -c "import huggingface_hub" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing huggingface_hub...
    python -m pip install huggingface_hub --quiet
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: Failed to install huggingface_hub.
        pause
        exit /b 1
    )
)

REM Optionally set China mirror
set "HF_MIRROR="
set /p HF_CHOICE="Use China mirror (hf-mirror.com)? [y/N]: "
if /i "!HF_CHOICE!"=="y" (
    set "HF_ENDPOINT=https://hf-mirror.com"
    echo Using mirror: !HF_ENDPOINT!
    echo.
)

if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"

echo.
echo Models to download:
echo   1. paraphrase-multilingual-MiniLM-L12-v2 (embedding, ~470 MB)
echo   2. EasyOCR ch_sim + en (OCR, ~100 MB download)
echo   3. SmolVLM-256M-Instruct (VLM, ~500 MB) - optional
echo.
set /p DOWNLOAD_VLM="Download SmolVLM? [Y/n]: "
if /i "!DOWNLOAD_VLM!"=="n" (
    set "SKIP_VLM=1"
) else (
    set "SKIP_VLM=0"
)

echo.
echo Downloading models to: %MODEL_DIR%
echo This may take a while on first run...
echo.

REM ---- Python download script ----
set "SCRIPT=%TEMP%\rag_kit_download.py"
(
echo import os, sys
echo from pathlib import Path
echo from huggingface_hub import snapshot_download, hf_hub_download
echo.
echo model_dir = os.environ.get("MODEL_DIR", os.path.expanduser("~/models"))
echo mirror = os.environ.get("HF_ENDPOINT", "")
echo if mirror:
echo     os.environ["HF_ENDPOINT"] = mirror
echo     print(f"Using mirror: {mirror}")
echo.
echo success = []
echo failed = []
echo.
echo # 1. Embedding model
echo print("\n[1/3] Downloading embedding model: paraphrase-multilingual-MiniLM-L12-v2")
echo print("  (~470 MB, 117M params, 50+ languages)")
echo try:
echo     snapshot_download(
echo         "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
echo         cache_dir=model_dir,
echo         resume_download=True,
echo     )
echo     print("  OK")
echo     success.append("embedding")
echo except Exception as e:
echo     print(f"  FAILED: {e}")
echo     failed.append("embedding")
echo.
echo # 2. EasyOCR models (Chinese + English)
echo print("\n[2/3] Downloading EasyOCR models: ch_sim + en")
echo print("  (~100 MB download, needed for scanned PDFs)")
echo try:
echo     import easyocr
echo     reader = easyocr.Reader(["ch_sim", "en"], gpu=False, download_enabled=True,
echo                             model_storage_directory=os.path.join(model_dir, "easyocr"))
echo     print("  OK")
echo     success.append("ocr")
echo except Exception as e:
echo     print(f"  FAILED: {e}")
echo     failed.append("ocr")
echo.
echo # 3. SmolVLM (optional)
echo skip_vlm = os.environ.get("SKIP_VLM", "0")
echo if skip_vlm != "1":
echo     print("\n[3/3] Downloading VLM model: SmolVLM-256M-Instruct")
echo     print("  (~500 MB, for chart/diagram captioning)")
echo     try:
echo         snapshot_download(
echo             "HuggingFaceTB/SmolVLM-256M-Instruct",
echo             cache_dir=model_dir,
echo             resume_download=True,
echo         )
echo         print("  OK")
echo         success.append("vlm")
echo     except Exception as e:
echo         print(f"  FAILED: {e}")
echo         print("  (VLM is optional — rag-kit works without it)")
echo         failed.append("vlm")
echo else:
echo     print("\n[3/3] Skipping VLM (user chose not to download)")
echo.
echo # Summary
echo print(f"\n{'='*60}")
echo print(f"  Download summary:")
echo print(f"    Succeeded: {', '.join(success) if success else 'none'}")
echo print(f"    Failed:    {', '.join(failed) if failed else 'none'}")
echo print(f"  Models cached in: {model_dir}")
echo print(f"{'='*60}")
echo.
echo if failed and not success:
echo     sys.exit(1)
echo elif failed:
echo     print("WARNING: Some models failed (non-critical if rag-kit can still work)")
) > "%SCRIPT%"

setlocal
if defined HF_ENDPOINT set "HF_ENDPOINT=%HF_ENDPOINT%"
set "MODEL_DIR=%MODEL_DIR%"
set "SKIP_VLM=%SKIP_VLM%"

python "%SCRIPT%"
set "DL_EXIT=%ERRORLEVEL%"
del "%SCRIPT%" 2>nul

echo.
if %DL_EXIT% NEQ 0 (
    echo ERROR: Model download failed. Check the errors above.
    echo You may need to try again or use a VPN/proxy.
    pause
    exit /b 1
)

echo ============================================================
echo   Download Complete
echo ============================================================
echo Models cached in: %MODEL_DIR%
echo You can now install rag-kit offline:
echo   scripts\install-windows.bat
echo.
pause
exit /b 0