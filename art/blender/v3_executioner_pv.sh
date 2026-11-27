#!/bin/bash
# 用法：bash v3_executioner_pv.sh <blend> <outdir> [flags...]
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
B=$(cygpath -w "$(realpath "$1")"); OD=$(realpath -m "$2"); mkdir -p "$OD"; O=$(cygpath -w "$OD"); shift 2
"$BL" --background --factory-startup --python v3_executioner_preview.py -- "$B" "$O" "$@" > "$OD/../log_pv.txt" 2>&1
grep -aE "Traceback|Error|DONE" "$OD/../log_pv.txt" | head
