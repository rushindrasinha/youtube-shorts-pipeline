#!/bin/bash
# ComfyUI Installation for M1 Pro 32GB Mac
# Installs ComfyUI + Wan 2.2 GGUF models + dependencies
# Usage: ./scripts/install_comfyui_m1.sh

set -e

COMFYUI_DIR="${HOME}/ComfyUI"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 ComfyUI Installation (M1 Pro Optimized)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if already installed
if [ -d "$COMFYUI_DIR" ]; then
    echo "✓ ComfyUI already installed at $COMFYUI_DIR"
    echo "  Updating..."
    cd "$COMFYUI_DIR"
    git pull
else
    echo "📥 Cloning ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_DIR"
    cd "$COMFYUI_DIR"
fi

echo ""
echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt

echo ""
echo "🔧 Installing ComfyUI Manager (for node management)..."
if [ ! -d "custom_nodes/ComfyUI-Manager" ]; then
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager
fi

echo ""
echo "🎥 Installing Video Helper Suite..."
if [ ! -d "custom_nodes/ComfyUI-VideoHelperSuite" ]; then
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git custom_nodes/ComfyUI-VideoHelperSuite
fi

echo ""
echo "🧠 Installing GGUF support (quantized models)..."
if [ ! -d "custom_nodes/ComfyUI-GGUF" ]; then
    git clone https://github.com/city96/ComfyUI-GGUF.git custom_nodes/ComfyUI-GGUF
fi

echo ""
echo "📥 Downloading Wan 2.2 GGUF Model (Q5_K_M - Best for M1 Pro)..."
echo "    This is ~3-4GB. Will take 10-15 minutes first time."
echo ""

MODELS_DIR="$COMFYUI_DIR/models/unet"
mkdir -p "$MODELS_DIR"

# Download Wan 2.2 5B GGUF (optimized for M1 Pro)
if [ ! -f "$MODELS_DIR/Wan2.2-I2V-5B-GGUF-Q5_K_M.gguf" ]; then
    echo "Downloading Wan 2.2 5B GGUF Q5_K_M..."
    cd "$MODELS_DIR"
    # Using huggingface-hub for reliable downloads
    python3 << 'EOF'
from huggingface_hub import hf_hub_download
import os

model_id = "QuantStack/Wan2.2-I2V-A5B-GGUF"
filename = "Wan2.2-I2V-5B-GGUF-Q5_K_M.gguf"

try:
    path = hf_hub_download(
        repo_id=model_id,
        filename=filename,
        cache_dir=os.getcwd()
    )
    print(f"✓ Downloaded to {path}")
except Exception as e:
    print(f"⚠️  Download failed: {e}")
    print("   Try manual download: https://huggingface.co/QuantStack/Wan2.2-I2V-A5B-GGUF")
    print("   Place file in: ~/ComfyUI/models/unet/")
EOF
else
    echo "  ✓ Wan 2.2 5B GGUF already present"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ComfyUI Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Start ComfyUI:"
echo "  cd ~/ComfyUI"
echo "  python main.py --listen 0.0.0.0 --port 8188"
echo ""
echo "📖 Access UI:"
echo "  http://localhost:8188"
echo ""
echo "💡 Tips:"
echo "  • Load workflow: ComfyUI UI → Load → Wan 2.2 I2V Lightning"
echo "  • Set resolution: 576×1024 (9:16 vertical Shorts)"
echo "  • Set frames: 65 (3-5 seconds)"
echo "  • Run headless: python main.py --headless --listen 127.0.0.1 --port 8188"
echo ""
echo "✨ n8n will call ComfyUI via API automatically"
echo ""
