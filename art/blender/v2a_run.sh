#!/bin/bash
# 建模 A：v2a_run.sh <sentinel|priest|gargoyle> [blender 參數...]
# Blender（headless）建模＋動作＋匯出 export_raw → 拼預覽圖 → gltf-transform 壓縮到 public/models（保留節點）→ P2 節點 scale 0 → 檢查
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
ID=$1; shift
M=boss_$ID
rm -f preview/_tiles/v2a_$M/*
"$BL" --background --factory-startup --python v2a_$ID.py -- "$@" 2>&1 | grep -E "Error|error|Traceback|File \"|ACTION|reach|TRIS|PARTS|P2 |WARN|EXPORT|META|DONE|line [0-9]+|ground|\[organic|\[assemble|\[bake\]"
python soul_sheet.py preview/_tiles/v2a_$M preview v2a_$M
if [[ " $* " != *" --quick "* ]] && [ -f export_raw/$M.glb ]; then
  python v2a_post.py --pre export_raw/$M.glb
  npx --yes gltf-transform optimize export_raw/$M.glb ../../public/models/$M.glb --compress meshopt --texture-compress webp --texture-size ${TEXSIZE:-1536} --flatten false --join false --palette false --instance false 2>&1 | tail -2
  python v2a_post.py ../../public/models/$M.glb
  ls -la ../../public/models/$M.glb
fi
