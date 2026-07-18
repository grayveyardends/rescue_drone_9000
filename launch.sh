#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== SAR Drone System ==="

if ! curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
  MODEL=~/models/gemma-4-E2B-it-Q8_0.gguf
  MMPROJ=~/models/mmproj-gemma-4-E2B-it-Q8_0.gguf
  if [ -f "$MODEL" ]; then
    echo "[llm] starting llama-server..."
    # NGL: GPU layers. 8GB GPU is mostly taken by Gazebo/desktop, so default to
    # CPU; run "NGL=999 ./launch.sh" for full GPU offload when headless.
    llama-server -m "$MODEL" --mmproj "$MMPROJ" -ngl "${NGL:-0}" --port 8080 -c 4096 &
  else
    echo "[llm] WARNING: model not found at $MODEL — dashboard will run without LLM"
  fi
fi

command -v xhost >/dev/null && xhost +local:docker >/dev/null || true
docker compose up --build

