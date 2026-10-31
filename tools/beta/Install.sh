#!/bin/sh
set -eu
kit_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Install Python 3.11 or newer, then run this helper again. See START-HERE.html.' >&2
    exit 1
fi
exec python3 -I "$kit_dir/installer.py" "$@"
