#!/bin/bash
# Start the TRIBE v2 Neural Processing API on port 8000.
set -euo pipefail

PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"

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

export TRIBE_DATA_DIR="${TRIBE_DATA_DIR:-$(cd "$(dirname "$0")/.." && pwd)/data}"

echo "Starting TRIBE v2 Neural Processing API..."
echo "  Data dir: $TRIBE_DATA_DIR"
echo "  Port:     8000"

exec uvicorn tribe_neural.api:app --host 0.0.0.0 --port 8000 --workers 1
