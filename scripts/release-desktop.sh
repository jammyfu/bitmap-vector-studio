#!/bin/bash
set -euo pipefail

# Bitmap Vector Studio Desktop Release Script
# Builds desktop app, generates update signatures, and prepares GitHub Release assets.
#
# Usage:
#   ./scripts/release-desktop.sh <version>
# Example:
#   ./scripts/release-desktop.sh v1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"
RELEASE_DIR="$PROJECT_ROOT/release"

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> (e.g., v1.0.0)"
    exit 1
fi

# Validate version format
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
    echo "Error: Version must start with 'v' followed by semver (e.g., v1.0.0)"
    exit 1
fi

echo "=== Bitmap Vector Studio Desktop Release ==="
echo "Version: $VERSION"
echo "Project: $PROJECT_ROOT"
echo ""

# Check prerequisites
command -v cargo >/dev/null 2>&1 || { echo "Error: cargo not found"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Error: npm not found"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Error: node not found"; exit 1; }

# Optional: gh CLI for upload
if command -v gh >/dev/null 2>&1; then
    HAS_GH=true
else
    HAS_GH=false
    echo "Warning: gh CLI not found. Release upload will be manual."
fi

# Clean and prepare release directory
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Build frontend
echo "[1/4] Installing and building frontend..."
cd "$DESKTOP_DIR"
npm install
npm run build

# Build Tauri app for current platform
echo "[2/4] Building Tauri app for current platform..."
cargo tauri build

# Collect artifacts
echo "[3/4] Collecting build artifacts..."
BUNDLE_DIR="$DESKTOP_DIR/src-tauri/target/release/bundle"

if [ ! -d "$BUNDLE_DIR" ]; then
    echo "Error: Bundle directory not found at $BUNDLE_DIR"
    exit 1
fi

# Copy all bundle artifacts and signatures
find "$BUNDLE_DIR" -type f \( \
    -name "*.msi" -o \
    -name "*.exe" -o \
    -name "*.dmg" -o \
    -name "*.AppImage" -o \
    -name "*.deb" -o \
    -name "*.rpm" -o \
    -name "*.sig" -o \
    -name "*.tar.gz" \
    \) -exec cp {} "$RELEASE_DIR/" \;

# Count copied artifacts
ARTIFACT_COUNT=$(find "$RELEASE_DIR" -type f | wc -l)
if [ "$ARTIFACT_COUNT" -eq 0 ]; then
    echo "Warning: No build artifacts found in $BUNDLE_DIR"
fi

# Generate latest.json template with signatures if available
echo "[4/4] Generating latest.json template..."

# Try to read signatures from .sig files
SIG_DARWIN="PLACEHOLDER_SIG_DARWIN"
SIG_DARWIN_ARM="PLACEHOLDER_SIG_DARWIN_ARM"
SIG_LINUX="PLACEHOLDER_SIG_LINUX"
SIG_WINDOWS="PLACEHOLDER_SIG_WINDOWS"

for sigfile in "$RELEASE_DIR"/*.sig; do
    [ -e "$sigfile" ] || continue
    sigcontent=$(cat "$sigfile" | tr -d '\n')
    fname=$(basename "$sigfile")
    if [[ "$fname" == *"darwin"* ]] || [[ "$fname" == *"macos"* ]] || [[ "$fname" == *"dmg"* ]]; then
        if [[ "$fname" == *"aarch64"* ]] || [[ "$fname" == *"arm"* ]]; then
            SIG_DARWIN_ARM="$sigcontent"
        else
            SIG_DARWIN="$sigcontent"
        fi
    elif [[ "$fname" == *"linux"* ]] || [[ "$fname" == *"appimage"* ]] || [[ "$fname" == *"AppImage"* ]]; then
        SIG_LINUX="$sigcontent"
    elif [[ "$fname" == *"windows"* ]] || [[ "$fname" == *"msi"* ]] || [[ "$fname" == *"nsis"* ]]; then
        SIG_WINDOWS="$sigcontent"
    fi
done

# Strip leading 'v' for file names
VERSION_NO_V="${VERSION#v}"

cat > "$RELEASE_DIR/latest.json" <<EOF
{
  "version": "$VERSION",
  "notes": "See CHANGELOG.md for release notes.",
  "pub_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "platforms": {
    "darwin-x86_64": {
      "signature": "$SIG_DARWIN",
      "url": "https://github.com/jammyfu/bitmap-vector-studio/releases/download/$VERSION/Bitmap.Vector.Studio_${VERSION_NO_V}_x64.dmg"
    },
    "darwin-aarch64": {
      "signature": "$SIG_DARWIN_ARM",
      "url": "https://github.com/jammyfu/bitmap-vector-studio/releases/download/$VERSION/Bitmap.Vector.Studio_${VERSION_NO_V}_aarch64.dmg"
    },
    "linux-x86_64": {
      "signature": "$SIG_LINUX",
      "url": "https://github.com/jammyfu/bitmap-vector-studio/releases/download/$VERSION/bitmap-vector-studio_${VERSION_NO_V}_amd64.AppImage"
    },
    "windows-x86_64": {
      "signature": "$SIG_WINDOWS",
      "url": "https://github.com/jammyfu/bitmap-vector-studio/releases/download/$VERSION/Bitmap.Vector.Studio_${VERSION_NO_V}_x64_en-US.msi"
    }
  }
}
EOF

echo ""
echo "=== Release artifacts prepared ==="
ls -la "$RELEASE_DIR"
echo ""

# Optional: create GitHub release and upload
if [ "$HAS_GH" = true ]; then
    echo "Creating GitHub release draft..."
    if gh release view "$VERSION" >/dev/null 2>&1; then
        echo "Release $VERSION already exists. Uploading assets..."
        gh release upload "$VERSION" "$RELEASE_DIR"/* --clobber
    else
        gh release create "$VERSION" \
            --title "Bitmap Vector Studio $VERSION" \
            --notes-file "$PROJECT_ROOT/RELEASE_NOTES.md" \
            --draft \
            "$RELEASE_DIR"/*
    fi
    echo "GitHub release updated."
else
    echo "Next steps (manual):"
    echo "1. Review and update signature placeholders in $RELEASE_DIR/latest.json if needed"
    echo "2. Create GitHub Release: $VERSION"
    echo "3. Upload all files from $RELEASE_DIR to the release"
    echo "4. Ensure latest.json is attached as 'latest.json' for the updater endpoint"
fi

echo ""
echo "Done."
