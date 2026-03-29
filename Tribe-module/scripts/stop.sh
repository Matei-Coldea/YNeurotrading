#!/bin/bash
# Stop all TRIBE v2 server processes.
set -euo pipefail

PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$PROJ_DIR/run"

echo "Stopping TRIBE v2 server..."

# 1. Kill the main start.sh process (triggers its cleanup trap)
if [ -f "$PID_DIR/start.pid" ]; then
    START_PID=$(cat "$PID_DIR/start.pid")
    if kill -0 "$START_PID" 2>/dev/null; then
        echo "Killing start.sh (PID $START_PID)..."
        kill "$START_PID" 2>/dev/null || true
        sleep 2
    fi
fi

# 2. Kill uvicorn master + child workers
if [ -f "$PID_DIR/uvicorn.pid" ]; then
    UVICORN_PID=$(cat "$PID_DIR/uvicorn.pid")
    if kill -0 "$UVICORN_PID" 2>/dev/null; then
        echo "Killing uvicorn (PID $UVICORN_PID)..."
        kill "$UVICORN_PID" 2>/dev/null || true
    fi
fi

# 3. Kill ARQ GPU workers
if [ -f "$PID_DIR/workers.pid" ]; then
    while read -r PID; do
        if kill -0 "$PID" 2>/dev/null; then
            echo "Killing ARQ worker (PID $PID)..."
            kill "$PID" 2>/dev/null || true
        fi
    done < "$PID_DIR/workers.pid"
fi

# 4. Wait a moment, then force-kill any stragglers
sleep 2
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    while read -r PID; do
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force-killing PID $PID..."
            kill -9 "$PID" 2>/dev/null || true
        fi
    done < "$pidfile"
done

# 5. Catch any orphaned processes by name (e.g. from prior crashed runs)
pkill -f "arq tribe_neural.worker" 2>/dev/null || true
pkill -f "uvicorn tribe_neural.api" 2>/dev/null || true

# 6. Clean up PID files
rm -f "$PID_DIR"/*.pid

# 7. Flush Redis job queue
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &>/dev/null; then
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" FLUSHALL >/dev/null
    echo "Redis queue flushed"
fi

echo "Server stopped."
