#!/bin/bash
# 用法：./run_boss.sh <gargoyle|priest|devourer> <stage...>（依序跑各階段並拼預覽圖）
cd "$(dirname "$0")"
B="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
N=boss_$1; shift
for st in "$@"; do
  "$B" --background --factory-startup --python build_$N.py -- $st 2>&1 | grep -v "WARNING: " | grep -E "Error|Traceback|File \"|WARN|\[organic|\[assemble|\[export|DONE|KeyError|line [0-9]+"
done
F=preview/_frames
python make_sheet.py views preview/${N}_views.jpg $F/${N}_front.png $F/${N}_side.png $F/${N}_back.png $F/${N}_q34.png
if ls $F/${N}__Idle__* >/dev/null 2>&1; then python make_sheet.py actions preview/${N}_actions.jpg $F $N; fi
