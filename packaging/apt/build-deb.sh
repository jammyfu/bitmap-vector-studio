#!/usr/bin/env bash
# build-deb.sh — Build a .deb package for bitmap-vector-studio using fpm
# Usage: ./build-deb.sh [VERSION]
set -euo pipefail

VERSION="${1:-0.3.0}"
PKG_NAME="bitmap-vector-studio"
MAINTAINER="Bitmap Vector Studio Contributors <maintainer@example.com>"
DESCRIPTION="Illustrator-like bitmap/raster to SVG vector conversion studio"

# Detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build/deb"

echo "[INFO] Building ${PKG_NAME}_${VERSION}_all.deb ..."

# Ensure fpm is available
if ! command -v fpm &>/dev/null; then
    echo "[ERROR] fpm is not installed. Install it first:"
    echo "  sudo apt-get install ruby-dev build-essential"
    echo "  sudo gem install --no-document fpm"
    exit 1
fi

# Prepare staging area
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/usr/lib/bitmap-vector-studio"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/DEBIAN"

# Create virtualenv and install package
python3 -m venv "${BUILD_DIR}/usr/lib/bitmap-vector-studio/venv"
"${BUILD_DIR}/usr/lib/bitmap-vector-studio/venv/bin/pip" install --upgrade pip
"${BUILD_DIR}/usr/lib/bitmap-vector-studio/venv/bin/pip" install "${PROJECT_ROOT}[api,smart]"

# Create wrapper script
cat > "${BUILD_DIR}/usr/bin/vector-studio" <<'EOF'
#!/usr/bin/env bash
set -e
VENV_DIR="/usr/lib/bitmap-vector-studio/venv"
exec "${VENV_DIR}/bin/vector-studio" "$@"
EOF
chmod +x "${BUILD_DIR}/usr/bin/vector-studio"

# Build .deb with fpm
fpm \
    -s dir \
    -t deb \
    -n "${PKG_NAME}" \
    -v "${VERSION}" \
    --architecture all \
    --maintainer "${MAINTAINER}" \
    --description "${DESCRIPTION}" \
    --depends "python3" \
    --depends "python3-venv" \
    --depends "libcairo2" \
    --depends "libffi8" \
    --prefix / \
    -C "${BUILD_DIR}" \
    --deb-no-default-config-files \
    "${BUILD_DIR}/usr/lib/bitmap-vector-studio" \
    "${BUILD_DIR}/usr/bin/vector-studio"

# Move result to dist
mkdir -p "${PROJECT_ROOT}/dist"
mv "*.deb" "${PROJECT_ROOT}/dist/" 2>/dev/null || true

echo "[OK] Debian package built."
ls -la "${PROJECT_ROOT}/dist/"*.deb 2>/dev/null || echo "Check current directory for .deb file"
