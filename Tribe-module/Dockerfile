FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# System dependencies needed by tribev2 (ffmpeg, espeak-ng for event segmentation)
RUN apt-get update -qq && \
    apt-get install -y -qq git ffmpeg espeak-ng && \
    rm -rf /var/lib/apt/lists/*

# Clone and install tribev2 first (heaviest layer, changes least often)
RUN git clone https://github.com/facebookresearch/tribev2.git /app/tribev2 && \
    cd /app/tribev2 && pip install --no-cache-dir -e '.[plotting]'

# Install GPU/science dependencies (separate layer for caching)
RUN pip install --no-cache-dir \
    nilearn nibabel scipy nimare nltools \
    fastapi 'uvicorn[standard]' pydantic numpy

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY scripts/ scripts/

# Install this package
RUN pip install --no-cache-dir -e .

# Make scripts executable
RUN chmod +x scripts/*.sh

# Data directory — mount a RunPod volume here to persist across restarts
ENV TRIBE_DATA_DIR=/app/data
RUN mkdir -p /app/data

EXPOSE 8000

# Entrypoint: run setup (idempotent, skips if data exists) then start server
COPY <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -euo pipefail

DATA_DIR="${TRIBE_DATA_DIR:-/app/data}"
mkdir -p "$DATA_DIR"

# Step 1: Generate NiMARE weights (~30 min first run, skipped if exists)
if [ ! -f "$DATA_DIR/neurosynth_weights.npz" ]; then
    echo "Generating NiMARE weight maps (first run only, ~30 min)..."
    python /app/scripts/generate_weights.py \
        --output "$DATA_DIR/neurosynth_weights.npz" \
        --neurosynth-dir "$DATA_DIR/neurosynth_data"
else
    echo "NiMARE weights already exist — skipping."
fi

# Step 2: Project signatures (~5 min first run, skipped if exists)
if [ ! -f "$DATA_DIR/vifs_surface.npy" ]; then
    echo "Projecting VIFS/PINES signatures..."
    python /app/scripts/project_signatures.py --output-dir "$DATA_DIR"
else
    echo "Signatures already exist — skipping."
fi

# Step 3: Validate VIFS transfer (~5 min first run, skipped if already done)
if [ ! -f "$DATA_DIR/vifs_validated" ] && [ ! -f "$DATA_DIR/vifs_validation_failed" ]; then
    if [ -n "${HF_TOKEN:-}" ]; then
        echo "Running VIFS validation..."
        python /app/scripts/validate_signatures.py --data-dir "$DATA_DIR" || {
            echo "WARNING: Validation failed — pipeline will use NiMARE-only fallback."
            touch "$DATA_DIR/vifs_validation_failed"
        }
    else
        echo "WARNING: HF_TOKEN not set — skipping VIFS validation."
    fi
else
    echo "Validation already completed — skipping."
fi

echo "Starting TRIBE v2 Neural Processing API on port 8000..."
exec uvicorn tribe_neural.api:app --host 0.0.0.0 --port 8000 --workers 1
EOF

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
