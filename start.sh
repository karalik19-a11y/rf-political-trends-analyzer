#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 required"
  exit 1
fi
python3 bootstrap.py "$@"
