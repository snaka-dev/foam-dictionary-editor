#!/usr/bin/env bash
set -euo pipefail

APP_NAME="foam-dictionary-editor"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[1/6] Checking project root..."
if [[ ! -f "main.py" ]]; then
  echo "ERROR: main.py was not found. Run this script from the project root." >&2
  exit 1
fi

if [[ ! -f "${APP_NAME}.spec" ]]; then
  echo "ERROR: ${APP_NAME}.spec was not found." >&2
  exit 1
fi

echo "[2/6] Installing packaging dependencies..."
"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install -r requirements-packaging.txt

echo "[3/6] Cleaning previous build artifacts..."
rm -rf build dist

echo "[4/6] Building Linux distribution with PyInstaller..."
"${PYTHON_BIN}" -m PyInstaller --noconfirm --clean "${APP_NAME}.spec"

echo "[5/6] Finalizing distribution..."
chmod +x "dist/${APP_NAME}/${APP_NAME}" || true

if [[ -f "README.md" ]]; then
  cp "README.md" "dist/${APP_NAME}/README.md"
fi

if [[ -f "README_ja.md" ]]; then
  cp "README_ja.md" "dist/${APP_NAME}/README_ja.md"
fi

cat > "dist/${APP_NAME}/README-runtime.txt" <<'EOF'
foam dictionary editor - Linux distribution package

Run:
  ./foam-dictionary-editor

Notes:
- This package was built with PyInstaller in onedir mode.
- Distribute the whole directory, not only the executable file.
- If the application does not start, inspect shared-library dependencies:
    ldd ./foam-dictionary-editor
- If a Qt platform plugin error appears, verify that the bundled Qt plugin
  directories exist in the distribution folder.
EOF

echo "[6/6] Build completed."
echo
echo "Executable:"
echo "  dist/${APP_NAME}/${APP_NAME}"
echo
echo "Top-level distribution contents:"
find "dist/${APP_NAME}" -maxdepth 2 | head -n 80
