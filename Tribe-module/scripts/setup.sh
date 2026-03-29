#!/bin/bash
# RunPod setup script — installs all dependencies and generates cached data.
# Idempotent: safe to re-run (each step checks if output already exists).
# All packages install into /workspace/venv so they persist across restarts.
set -euo pipefail

PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Load .env file if it exists
if [ -f "$PROJ_DIR/.env" ]; then
    set -a
    source "$PROJ_DIR/.env"
    set +a
fi

DATA_DIR="${TRIBE_DATA_DIR:-$PROJ_DIR/data}"

# ── 0. Persistent venv in /workspace ────────────────────────────────
VENV_DIR="/workspace/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "── Creating persistent venv at $VENV_DIR ──"
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo "=== TRIBE v2 Neural Processing Module Setup ==="
echo "Project dir: $PROJ_DIR"
echo "Data dir:    $DATA_DIR"
echo "Venv:        $VENV_DIR"

# ── 1. System dependencies ──────────────────────────────────────────
echo ""
echo "── Installing system packages ──"
apt-get update -qq && apt-get install -y -qq git ffmpeg espeak-ng > /dev/null 2>&1
echo "  Done."

# ── 2. Clone and install tribev2 ─────────────────────────────────────
echo ""
echo "── Setting up TRIBE v2 ──"
if [ ! -d "$PROJ_DIR/tribev2" ]; then
    git clone https://github.com/facebookresearch/tribev2.git "$PROJ_DIR/tribev2"
fi
cd "$PROJ_DIR/tribev2"
pip install -e '.[plotting]' --quiet

# ── 3. Install Python dependencies ──────────────────────────────────
echo ""
echo "── Installing Python dependencies ──"
pip install --quiet nilearn nibabel scipy nimare nltools
pip install --quiet fastapi 'uvicorn[standard]' pydantic
pip install --quiet pytest pytest-asyncio httpx

# ── 4. Install this package ──────────────────────────────────────────
echo ""
echo "── Installing tribe-neural package ──"
cd "$PROJ_DIR" && pip install -e . --quiet

# ── 5. Create data directory ─────────────────────────────────────────
mkdir -p "$DATA_DIR"

# ── 6. Generate NiMARE weights (~30 min on first run) ────────────────
echo ""
echo "── NiMARE weight generation ──"
if [ ! -f "$DATA_DIR/neurosynth_weights.npz" ]; then
    echo "  Generating meta-analytic weights (this takes ~30 minutes)..."
    python "$PROJ_DIR/scripts/generate_weights.py" \
        --output "$DATA_DIR/neurosynth_weights.npz" \
        --neurosynth-dir "$DATA_DIR/neurosynth_data"
else
    echo "  Weights already exist — skipping."
fi

# ── 7. Download and project signatures ───────────────────────────────
echo ""
echo "── Signature projection ──"
if [ ! -f "$DATA_DIR/vifs_surface.npy" ]; then
    echo "  Downloading and projecting VIFS/PINES signatures..."
    python "$PROJ_DIR/scripts/project_signatures.py" \
        --output-dir "$DATA_DIR"
else
    echo "  Signatures already exist — skipping."
fi

# ── 8. Validate VIFS transfer ────────────────────────────────────────
echo ""
echo "── Signature validation ──"
if [ ! -f "$DATA_DIR/vifs_validated" ] && [ ! -f "$DATA_DIR/vifs_validation_failed" ]; then
    if [ -z "${HF_TOKEN:-}" ]; then
        echo "  WARNING: HF_TOKEN not set — skipping validation."
        echo "  Run manually: python scripts/validate_signatures.py --data-dir $DATA_DIR"
    else
        echo "  Running VIFS transfer validation (~5 min)..."
        python "$PROJ_DIR/scripts/validate_signatures.py" \
            --data-dir "$DATA_DIR" || {
            echo "  WARNING: Validation script failed. Pipeline will use NiMARE-only fallback."
            touch "$DATA_DIR/vifs_validation_failed"
        }
    fi
else
    echo "  Validation already completed — skipping."
fi

echo ""
echo "=== Setup complete ==="
echo "Start the server with: bash scripts/start.sh"
