#!/bin/bash
# usage: run_soul.sh <hero|sentinel|executioner> [build args...]
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
case "$1" in hero) M=hero_knight;; sentinel) M=boss_sentinel;; executioner) M=boss_executioner;; esac
S=build_soul_$1.py; shift
rm -f preview/_tiles/$M/act_* preview/_tiles/$M/strip_*
"$BL" --background --factory-startup --python $S -- "$@" 2>&1 | grep -E "WARN 權|Error|error|Traceback|DUP|TRIS|DONE|File \"|ACTION|reach|line |PARTS"
python soul_sheet.py preview/_tiles/$M preview $M
