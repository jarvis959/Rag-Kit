#!/usr/bin/env bash
# download-models.sh — Pre-download all models for offline rag-kit use
#
# Usage:
#   chmod +x download-models.sh
#   ./download-models.sh
#
# Models are cached in ~/models/ by default.
# Set HF_ENDPOINT=https://hf-mirror.com for users behind firewalls.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  rag-kit - Model Downloader${NC}"
echo -e "${BLUE}  Downloads all models for offline use${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo "This script pre-downloads models to ~/models/"
echo "so rag-kit can work fully offline after installation."
echo ""

MODEL_DIR="${MODEL_DIR:-$HOME/models}"
mkdir -p "$MODEL_DIR"

# Check Python
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}ERROR: Python not found. Please install Python 3.10+ first.${NC}"
    exit 1
fi

# Install huggingface_hub if needed
if ! $PYTHON -c "import huggingface_hub" 2>/dev/null; then
    echo "Installing huggingface_hub..."
    $PYTHON -m pip install huggingface_hub -q || {
        echo -e "${RED}ERROR: Failed to install huggingface_hub.${NC}"
        exit 1
    }
fi

# China mirror
if [ -z "${HF_ENDPOINT:-}" ]; then
    echo -n "Use China mirror (hf-mirror.com)? [y/N]: "
    read -r USE_MIRROR
    if [ "$USE_MIRROR" = "y" ] || [ "$USE_MIRROR" = "Y" ]; then
        export HF_ENDPOINT="https://hf-mirror.com"
        echo "Using mirror: $HF_ENDPOINT"
        echo ""
    fi
fi

echo ""
echo "Models to download:"
echo "  1. paraphrase-multilingual-MiniLM-L12-v2 (embedding, ~470 MB)"
echo "  2. EasyOCR ch_sim + en (OCR, ~100 MB download)"
echo "  3. SmolVLM-256M-Instruct (VLM, ~500 MB) - optional"
echo ""

echo -n "Download SmolVLM? [Y/n]: "
read -r DOWNLOAD_VLM
SKIP_VLM=0
if [ "$DOWNLOAD_VLM" = "n" ] || [ "$DOWNLOAD_VLM" = "N" ]; then
    SKIP_VLM=1
fi

echo ""
echo "Downloading models to: $MODEL_DIR"
echo "This may take a while on first run..."
echo ""

# ---- Python model downloader ----
$PYTHON << 'PYEOF'
import os
import sys
from pathlib import Path

model_dir = os.environ.get("MODEL_DIR", os.path.expanduser("~/models"))
skip_vlm = int(os.environ.get("SKIP_VLM", "0"))

success = []
failed = []

# 1. Embedding model
print("\n[1/3] Downloading embedding model: paraphrase-multilingual-MiniLM-L12-v2")
print("  (~470 MB, 117M params, 50+ languages)")
try:
    from huggingface_hub import snapshot_download
    snapshot_download(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        cache_dir=model_dir,
        resume_download=True,
    )
    print("  OK")
    success.append("embedding")
except Exception as e:
    print(f"  FAILED: {e}")
    failed.append("embedding")

# 2. EasyOCR models
print("\n[2/3] Downloading EasyOCR models: ch_sim + en")
print("  (~100 MB download, needed for scanned PDFs)")
try:
    import easyocr
    reader = easyocr.Reader(
        ["ch_sim", "en"],
        gpu=False,
        download_enabled=True,
        model_storage_directory=os.path.join(model_dir, "easyocr"),
    )
    print("  OK")
    success.append("ocr")
except Exception as e:
    print(f"  FAILED: {e}")
    # Try installing easyocr if missing
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "easyocr", "-q"])
        import easyocr
        easyocr.Reader(
            ["ch_sim", "en"],
            gpu=False,
            download_enabled=True,
            model_storage_directory=os.path.join(model_dir, "easyocr"),
        )
        print("  OK (after installing easyocr)")
        success.append("ocr")
    except Exception as e2:
        print(f"  FAILED: {e2}")
        failed.append("ocr")

# 3. SmolVLM (optional)
if skip_vlm != 1:
    print("\n[3/3] Downloading VLM model: SmolVLM-256M-Instruct")
    print("  (~500 MB, for chart/diagram captioning)")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            "HuggingFaceTB/SmolVLM-256M-Instruct",
            cache_dir=model_dir,
            resume_download=True,
        )
        print("  OK")
        success.append("vlm")
    except Exception as e:
        print(f"  FAILED: {e}")
        print("  (VLM is optional — rag-kit works without it)")
        failed.append("vlm")
else:
    print("\n[3/3] Skipping VLM (user chose not to download)")

# Summary
print(f"\n{'='*60}")
print(f"  Download summary:")
print(f"    Succeeded: {', '.join(success) if success else 'none'}")
print(f"    Failed:    {', '.join(failed) if failed else 'none'}")
print(f"  Models cached in: {model_dir}")
print(f"{'='*60}")

if failed and not success:
    sys.exit(1)
elif failed:
    print("WARNING: Some models failed (non-critical if rag-kit can still work)")
PYEOF

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -ne 0 ]; then
    echo -e "${RED}ERROR: Model download failed. Check the errors above.${NC}"
    echo "You may need to try again or use a VPN/proxy."
    exit 1
fi

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Download Complete${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Models cached in: $MODEL_DIR"
echo "You can now install rag-kit offline:"
echo "  ./scripts/install-dgx-spark.sh"
echo ""

# Linux doesn't have 'pause'; just exit.
exit 0