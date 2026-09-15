#!/usr/bin/env bash
# Intelligent ML Studio - Linux / macOS Verification Wrapper
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo " Starting Intelligent ML Studio Verification Runner"
echo "============================================================"

if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "ERROR: Python is not installed or not in PATH."
    exit 1
fi

$PYTHON_CMD "$ROOT_DIR/scripts/verify.py" "$@"
