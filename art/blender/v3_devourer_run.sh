#!/bin/bash
# v3 噬語魔王：貼圖產生 → Blender 建模＋烘焙＋動作＋匯出 → 預覽 → 壓縮到 public/models → 後處理 → clipmeta 合併 → 檢查
# 用法：bash art/blender/v3_devourer_run.sh [--quick] [--nobake] [--skip-build] [--noprev]
#   --nobake：沿用 textures/baked/v3_devourer_* 既有烘焙（只改動作時用，v4 起）
#   暫存／log：art/v4/tmp/devourer（v4 起；C: 槽滿）
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
mkdir -p ../v4/tmp/devourer; TMPD="$(cd ../v4/tmp/devourer && pwd)"
export TEMP="$TMPD" TMP="$TMPD"
LOG="$TMPD/log_build.txt"
M=boss_devourer
python v3_devourer_tex.py
if [[ " $* " != *" --skip-build "* ]]; then
  "$BL" --background --factory-startup --python v3_devourer_model.py -- $( [[ " $* " == *" --quick "* ]] && echo --quick ) $( [[ " $* " == *" --nobake "* ]] && echo --nobake ) > "$LOG" 2>&1
  grep -aE "Traceback|Error|rror:|CAPE|WING|SWORD|TRIS|PART |X3PART|ACTION|reach|ground|META|DONE|line [0-9]+" "$LOG" | cut -c1-220
fi
BLEND=source/v3_devourer.blend; [[ " $* " == *" --quick "* ]] && BLEND=source/v3_devourer_quick.blend
"$BL" --background --factory-startup --python v3_devourer_measure.py -- $BLEND "$TMPD/measure.md" > "$TMPD/log_measure.txt" 2>&1
grep -aE "^\||H（|Traceback" "$TMPD/log_measure.txt"
# 逐片段逐格最低點（地面）檢查 → $TMPD/ground.md
"$BL" --background --factory-startup --python v3_devourer_groundcheck.py -- $BLEND "$TMPD/ground.md" > "$TMPD/log_ground.txt" 2>&1
grep -aE "✗|bad=|Traceback" "$TMPD/log_ground.txt"
if [[ " $* " != *" --noprev "* ]]; then
  "$BL" --background --factory-startup --python v3_devourer_preview.py -- $BLEND --set compare,views,close,sil > "$TMPD/log_prev.txt" 2>&1
  grep -aE "Traceback|Error" "$TMPD/log_prev.txt"
  python v3_devourer_sheet.py
fi
if [[ " $* " != *" --quick "* ]] && [ -f export_raw/$M.glb ]; then
  cp export_raw/$M.glb "$TMPD/$M.pre.glb"
  python v3_devourer_post.py --pre "$TMPD/$M.pre.glb"
  # 法線／ORM 縮到 ${NRMSIZE:-1536}（檔案大小 ≤4.5 MB），底色與書頁保留 2048；--prune false 保留 Tip_Weapon 空節點
  npx --yes gltf-transform resize "$TMPD/$M.pre.glb" "$TMPD/$M.rs.glb" --width ${NRMSIZE:-1536} --height ${NRMSIZE:-1536} --pattern "*_normal*" 2>&1 | tail -1
  npx --yes gltf-transform resize "$TMPD/$M.rs.glb" "$TMPD/$M.rs2.glb" --width ${NRMSIZE:-1536} --height ${NRMSIZE:-1536} --pattern "*_orm*" 2>&1 | tail -1
  npx --yes gltf-transform optimize "$TMPD/$M.rs2.glb" ../../public/models/$M.glb --compress meshopt --texture-compress webp     --texture-size ${TEXSIZE:-2048} --flatten false --join false --palette false --instance false --simplify false --prune false 2>&1 | tail -2
  rm -f "$TMPD/$M.rs.glb" "$TMPD/$M.rs2.glb"
  python v3_devourer_post.py ../../public/models/$M.glb
  python merge_clipmeta.py
  python check_soul_glb.py | grep -A6 "boss_devourer"
fi
