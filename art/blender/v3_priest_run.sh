#!/bin/bash
# v3 霜冠祭司一鍵流程：v3_priest_run.sh [--skipbuild] [blender 參數...]
# Blender 建模＋烘焙＋動作 → export_raw（未壓縮，保留）→ P2 群組節點（v2a_post --pre）→ gltf-transform（meshopt＋webp 2048）
# → P2 scale 0（v2a_post）→ merge_clipmeta → check_soul_glb → 量測
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
M=boss_priest
TMP="../v4/tmp/priest"   # v1.3.0：暫存改放 art/v4/tmp/priest（烘焙貼圖快取仍在 art/v3/tmp/priest/baked，由 build 腳本重用）
mkdir -p "$TMP"
if [ "$1" != "--skipbuild" ]; then
  "$BL" --background --factory-startup --python v3_priest_build.py -- "$@" > "$TMP/log_build.txt" 2>&1
  grep -E "Error|Traceback|File \"|reach|TRIS|P2 |WARN|EXPORT|META|DONE|BAKED" "$TMP/log_build.txt" | grep -v "^  reach" | tail -40
fi
cp export_raw/$M.glb "$TMP/$M.pre.glb"
python v2a_post.py --pre "$TMP/$M.pre.glb"
# B 圖集（臉、手、金屬、經書）的法線圖細節雜，2048 webp 超過 1 MB：壓縮前只把這一張縮到 1536，其餘維持 2048
../../node_modules/.bin/gltf-transform resize "$TMP/$M.pre.glb" "$TMP/$M.rs.glb" --width 1536 --height 1536 --pattern "*B_normal*" 2>&1 | tail -1
mv "$TMP/$M.rs.glb" "$TMP/$M.pre.glb"
# v1.3.0：刪掉整段都等於靜止值的 translation／scale 通道（播放無作用，卻佔 JSON＋資料數百 KB；新招加入後要靠這步才 ≤4.5 MB）
node v4_priest_trimanim.mjs "$TMP/$M.pre.glb"
../../node_modules/.bin/gltf-transform optimize "$TMP/$M.pre.glb" ../../public/models/$M.glb --compress meshopt --texture-compress webp \
  --texture-size ${TEXSIZE:-2048} --flatten false --join false --palette false --instance false --simplify false 2>&1 | tail -2
python v2a_post.py ../../public/models/$M.glb
rm -f "$TMP/$M.pre.glb"
python merge_clipmeta.py
python check_soul_glb.py | grep -A6 "boss_priest"
"$BL" --background --factory-startup --python v3_priest_measure.py 2>/dev/null | grep -vE "^(Blender|Read|TBB|Info|Warning|Import|Fra|Data|  )" | tail -24
"$BL" --background --factory-startup --python v3_priest_ground.py -- 1 "$TMP/ground.txt" 2>/dev/null | grep GROUND
