#!/usr/bin/env bash
set -euo pipefail
ollama pull qwen3:14b
ollama pull deepseek-r1:14b
ollama pull nomic-embed-text
cat > /tmp/Modelfile <<'MF'
FROM qwen3:14b
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
PARAMETER repeat_penalty 1.1
SYSTEM "You are an institutional trading analyst. Reason only from provided engine outputs and retrieved knowledge. Never invent price levels. Output strict JSON."
MF
ollama create tradinggpt-analyst -f /tmp/Modelfile
echo "models ready"
