#!/bin/bash
# Start the TRIBE v2 Neural Processing API with ARQ worker architecture.
#
#   Redis  ──  ARQ GPU worker (loads model, processes jobs)
#          └─  FastAPI (CPU-only, multiple uvicorn workers)
#
set -euo pipefail

PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$PROJ_DIR/run"
mkdir -p "$PID_DIR"

# Load .env file if it exists
if [ -f "$PROJ_DIR/.env" ]; then
    set -a
    source "$PROJ_DIR/.env"
    set +a
fi

if [ -z "${HF_TOKEN:-}" ]; then
    echo "ERROR: HF_TOKEN not set. Add it to .env or export it." >&2
    exit 1
fi

# Activate persistent venv
VENV_DIR="/workspace/venv"
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

# Persistent binaries (ffmpeg, etc.) installed under /workspace
export PATH="/workspace/bin:$PATH"

# All caches under /workspace for RunPod persistence
export TRIBE_DATA_DIR="${TRIBE_DATA_DIR:-$PROJ_DIR/data}"
export HF_HOME="/workspace/.cache/huggingface"
export XDG_CACHE_HOME="/workspace/.cache"
export NILEARN_DATA_DIR="/workspace/.cache/nilearn"
export PIP_CACHE_DIR="/workspace/.cache/pip"

# Skip HuggingFace Hub network checks — models are already cached locally
export HF_HUB_OFFLINE=1

# Redis
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"

# API tuning
API_WORKERS="${API_WORKERS:-4}"
API_PORT="${API_PORT:-8000}"
GPU_WORKERS="${GPU_WORKERS:-5}"

cleanup() {
    echo "Shutting down..."
    kill -- -$$ 2>/dev/null || true
    rm -f "$PID_DIR"/*.pid
    wait
}
trap cleanup EXIT INT TERM

# Write main process PID
echo $$ > "$PID_DIR/start.pid"

# ── 1. Redis ─────────────────────────────────────────────────────────
if ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &>/dev/null; then
    echo "Starting Redis on port $REDIS_PORT..."
    redis-server --port "$REDIS_PORT" --daemonize yes \
        --save "" --appendonly no \
        --maxmemory 256mb --maxmemory-policy allkeys-lru
    # Wait for Redis to be ready
    for i in $(seq 1 10); do
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &>/dev/null && break
        sleep 0.5
    done
fi
echo "Redis: $REDIS_HOST:$REDIS_PORT"

# ── 2. ARQ GPU worker(s) ────────────────────────────────────────────
echo "Starting $GPU_WORKERS ARQ GPU worker(s)..."
for i in $(seq 1 "$GPU_WORKERS"); do
    arq tribe_neural.worker.WorkerSettings &
    echo $! >> "$PID_DIR/workers.pid"
done

# Wait for GPU worker to load the model (check Redis for worker heartbeat)
echo "Waiting for GPU worker to load model..."
for i in $(seq 1 120); do
    # ARQ workers register a health check key once startup() completes
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" keys "arq:*:health-check" 2>/dev/null | grep -q "health-check"; then
        echo "GPU worker ready after ${i}s"
        break
    fi
    sleep 1
    if [ "$i" -eq 120 ]; then
        echo "WARNING: GPU worker may still be loading (waited 120s)"
    fi
done

# ── 3. FastAPI (CPU-only, multiple workers) ──────────────────────────
echo ""
echo "Starting TRIBE v2 Neural Processing API..."
echo "  API workers: $API_WORKERS"
echo "  GPU workers: $GPU_WORKERS"
echo "  Port:        $API_PORT"
echo "  Redis:       $REDIS_HOST:$REDIS_PORT"
echo ""

uvicorn tribe_neural.api:app \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --workers "$API_WORKERS" &
echo $! > "$PID_DIR/uvicorn.pid"

echo "Server running. PID files in $PID_DIR"
echo "Stop with: bash scripts/stop.sh"

# Wait for all children — keeps the script alive so the trap works
wait
