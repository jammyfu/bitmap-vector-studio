#!/bin/bash
set -euo pipefail

# Bitmap Vector Studio Desktop Build Script (macOS / Linux)
# Builds the Tauri desktop application for the current platform.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"

echo "=== Bitmap Vector Studio Desktop Build ==="
echo "Platform: $(uname -s)"
echo ""

# Check prerequisites
command -v node >/dev/null 2>&1 || { echo "Error: Node.js not found. Please install Node.js 20+."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Error: npm not found."; exit 1; }
command -v cargo >/dev/null 2>&1 || { echo "Error: Rust / cargo not found. Please install Rust."; exit 1; }

# Verify Node version
NODE_MAJOR=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_MAJOR" -lt 18 ]; then
    echo "Error: Node.js 18+ required (found $(node -v))."
    exit 1
fi

# Install frontend dependencies
echo "[1/3] Installing frontend dependencies..."
cd "$DESKTOP_DIR"
npm install

# Build frontend
echo "[2/3] Building frontend..."
npm run build

# Build Tauri app
echo "[3/3] Building Tauri app..."
cargo tauri build

echo ""
echo "=== Build complete ==="
echo "Artifacts located in: $DESKTOP_DIR/src-tauri/target/release/bundle/"
