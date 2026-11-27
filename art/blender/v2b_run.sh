#!/bin/bash
# 建模 B v2：建模＋烘焙＋動作＋匯出＋預覽圖＋壓縮到 public/models＋隱藏型態節點＋檢查。
# 用法：bash v2b_run.sh <executioner|devourer> [blender args...]
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
ID=$1; shift
M=boss_$ID
LOG=${V2B_LOG:-/dev/null}
"$BL" --background --factory-startup --python v2b_$ID.py -- "$@" > "$LOG" 2>&1
grep -aE "Traceback|Error:|TRIS_|PART |ACTION|META|DONE" "$LOG" | cut -c1-200
python soul_sheet.py preview/_tiles/v2b_$ID preview v2b_$ID
npx gltf-transform optimize export_raw/$M.glb ../../public/models/$M.glb --compress meshopt --texture-compress webp \
  --texture-size ${TEXSIZE:-1536} --flatten false --join false --palette false --instance false 2>&1 | tail -2
python v2b_glbpost.py ../../public/models/$M.glb --hide
