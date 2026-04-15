#!/bin/bash
set -e

# 🐳 One-Command Docker + Ollama + n8n Setup for YouTube Shorts Factory
# Usage: ./scripts/setup_docker_stack.sh

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐳 YouTube Shorts Factory Setup (Docker + Ollama + n8n)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Docker
echo "✓ Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install from https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo "  ✓ Docker is installed: $(docker --version)"

# Check Docker is running
if ! docker ps &> /dev/null; then
    echo "❌ Docker is not running. Start Docker Desktop and try again."
    exit 1
fi
echo "  ✓ Docker daemon is running"

# Check Python
echo "✓ Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
echo "  ✓ Python $PYTHON_VERSION found"

# Check Verticals is installed
echo "✓ Checking Verticals v3..."
if ! python3 -m verticals niches &> /dev/null; then
    echo "⚠️  Verticals not fully configured. Installing dependencies..."
    pip install -r requirements.txt
fi
echo "  ✓ Verticals is ready"

# Create .env file
echo "✓ Creating .env file..."
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# n8n Encryption Key (change this to something random)
N8N_ENCRYPTION_KEY=$(openssl rand -base64 32)

# Optional: YouTube API key for uploads
# YOUTUBE_API_KEY=your-key-here

# Optional: Discord webhook for notifications
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID
EOF
    echo "  ✓ Created .env file (customize if needed)"
else
    echo "  ℹ️  .env file already exists, keeping it"
fi

# Start Docker services
echo ""
echo "🚀 Starting Docker services..."
echo "  (ollama, redis, n8n)"
echo ""
docker compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy (this may take 30-60 seconds)..."
sleep 10

# Check Ollama
echo -n "  Waiting for Ollama... "
for i in {1..30}; do
    if docker compose exec ollama ollama list &> /dev/null; then
        echo "✓"
        break
    fi
    echo -n "."
    sleep 2
done

# Check Redis
echo -n "  Waiting for Redis... "
for i in {1..20}; do
    if docker compose exec redis redis-cli ping &> /dev/null; then
        echo "✓"
        break
    fi
    echo -n "."
    sleep 1
done

# Check n8n
echo -n "  Waiting for n8n... "
for i in {1..20}; do
    if curl -s http://localhost:5678 &> /dev/null; then
        echo "✓"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "✅ Docker services are running!"
echo ""

# Pull Ollama model
echo "📦 Pulling Ollama model (llama2:13b)..."
echo "   This downloads ~7GB. First time only, then cached."
docker compose exec ollama ollama pull llama2:13b &

# Show status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Access n8n at: http://localhost:5678"
echo ""
echo "📖 Next Steps:"
echo "  1. Open http://localhost:5678 in your browser"
echo "  2. Click 'New Workflow' → 'Import from file'"
echo "  3. Select: scripts/n8n_workflow_full_async.json"
echo "  4. Click 'Activate' (top right)"
echo "  5. Workflow runs automatically every 60 minutes"
echo ""
echo "💡 To test immediately:"
echo "  • In n8n, click '⏰ Schedule Trigger' node"
echo "  • Click 'Test' button"
echo "  • Watch first video generate (2-3 min)"
echo ""
echo "📊 Monitor:"
echo "  • docker compose logs -f n8n"
echo "  • docker compose ps"
echo ""
echo "💬 For detailed setup, read: DOCKER_OLLAMA_SETUP.md"
echo ""
echo "Happy Shorts! 🎬"
