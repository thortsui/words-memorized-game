#!/bin/bash
# v3 sentinel 一鍵流程：bash art/blender/v3_sentinel_run.sh [--quick] [--noanim] [--only A,B] [--norender]  （--nobake：沿用 v3/tmp/sentinel/baked 的烘焙圖）
# Blender（headless）建模＋烘焙＋動作＋匯出 export_raw → 預覽拼圖 → P2 群組節點 → gltf-transform（meshopt、webp 2048，保留節點）→ P2 scale 0 → 量測 → 檢查
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
M=boss_sentinel
TMP=../v3/tmp/sentinel
mkdir -p $TMP/meas
"$BL" --background --factory-startup --python v3_sentinel_build.py -- "$@" > $TMP/log_build.txt 2>&1
grep -E "Error|Traceback|File \"|ACTION|reach|TRIS|P2 |WARN|EXPORT|META|DONE|ROOTS|ground|BAKE" $TMP/log_build.txt | grep -v "^  PARTTRI"
python v3_sentinel_sheet.py
if [[ " $* " != *" --quick "* ]] && [[ " $* " != *" --only "* ]] && [ -f export_raw/$M.glb ]; then
  python v3_sentinel_post.py --pre export_raw/$M.glb
  ../../node_modules/.bin/gltf-transform optimize export_raw/$M.glb ../../public/models/$M.glb --compress meshopt --texture-compress webp \
    --texture-size ${TEXSIZE:-2048} --flatten false --join false --palette false --instance false --simplify false 2>&1 | tail -2
  python v3_sentinel_post.py ../../public/models/$M.glb
  ls -la ../../public/models/$M.glb
  "$BL" --background --factory-startup --python v3_sentinel_measure.py -- export_raw/$M.glb $TMP/meas/v3.json 2>&1 | grep MEAS
  python merge_clipmeta.py
  python check_soul_glb.py | grep -A6 "boss_sentinel"
fi
