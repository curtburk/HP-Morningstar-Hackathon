#!/bin/bash

# Download hackathon models from the HP-Morningstar-Hackathon repo
# to the ZGX Nano for local serving via Ollama or vLLM

echo "================================================"
echo "HP + Morningstar Hackathon Model Download"
echo "================================================"
echo ""
echo "Models to download:"
echo "  1. Qwen3-14B-AWQ        (~10 GB)  - Agent LLM, strong structured output"
echo "  2. Qwen3.6-27B-FP8      (~31 GB)  - Higher-capability agent reasoning"
echo "  3. Ministral-3-8B       (~479 MB)  - Lightweight/fast iteration"
echo ""
echo "Total: ~41 GB"
echo ""

cd ~/Desktop/Hackathon-prep

echo "Creating local models folder..."
mkdir -p models

python3 -m venv 'hack-env'
source hack-env/bin/activate

pip install -q huggingface_hub

echo ""
echo "================================================"
echo "[1/3] Downloading Qwen3-14B-AWQ (~10 GB)..."
echo "================================================"
python3 << 'EOF'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="curtburk/HP-Morningstar-Hackathon",
    allow_patterns="Qwen--Qwen3-14B-AWQ/**",
    local_dir="./models"
)
EOF

echo ""
echo "================================================"
echo "[2/3] Downloading Qwen3.6-27B-FP8 (~31 GB)..."
echo "================================================"
python3 << 'EOF'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="curtburk/HP-Morningstar-Hackathon",
    allow_patterns="Qwen--Qwen3.6-27B-FP8/**",
    local_dir="./models"
)
EOF

echo ""
echo "================================================"
echo "[3/3] Downloading Ministral-3-8B (~479 MB)..."
echo "================================================"
python3 << 'EOF'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="curtburk/HP-Morningstar-Hackathon",
    allow_patterns="mistralai--Ministral-3-8B-Instruct-2512/**",
    local_dir="./models"
)
EOF

deactivate

echo ""
echo "================================================"
echo "✅ All models downloaded to ./models/"
echo "================================================"
echo ""
echo "Contents:"
du -sh models/*/
echo ""
echo "Next steps:"
echo "  - Serve with Ollama:  ollama create <name> -f Modelfile"
echo "  - Serve with vLLM:    vllm serve ./models/Qwen--Qwen3-14B-AWQ"
echo "  - Or load directly with transformers"
