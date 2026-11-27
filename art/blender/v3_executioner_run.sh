#!/bin/bash
# v3 暗影行刑者：建模＋烘焙＋動作＋匯出 → 預覽／並排比較圖 → 壓縮到 public/models → P2 節點 scale 0 → 合併 clipmeta → 檢查。
# 用法：bash art/blender/v3_executioner_run.sh [--nopv] [--nobake]（--nobake：幾何沒變時沿用上次烘焙的貼圖，只重做動作／匯出）
# 烘焙預設用 CPU（GPU 被其他 Blender 佔用時會 out of memory）；BAKE_CPU= 空字串可改回 GPU。
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
T=../v3/tmp/executioner; mkdir -p $T
export BAKE_CPU=${BAKE_CPU-1}
NB=""; for a in "$@"; do [ "$a" = "--nobake" ] && NB="--nobake"; done
"$BL" --background --factory-startup --python v3_executioner.py -- $NB > $T/log_full.txt 2>&1
grep -aE "Traceback|Error|MEASURE|AXE|TRIS_|PART |reach|DONE" $T/log_full.txt | cut -c1-220
grep -aq "DONE boss_executioner" $T/log_full.txt || { echo "BUILD FAILED"; exit 1; }
if [ "$1" != "--nopv" ]; then
  rm -rf $T/pv; bash v3_executioner_pv.sh source/v3_executioner.blend $T/pv --views --close --p2
  python v3_executioner_compare.py $T/pv preview
  rm -rf $T/pva; bash v3_executioner_pv.sh source/v3_executioner.blend $T/pva --acts
  python soul_sheet.py $T/pva preview v3_executioner > /dev/null
fi
"$BL" --background source/v3_executioner.blend --python v3_executioner_ground.py -- "$(cygpath -w "$(realpath $T)")/ground.json" 2>&1 | grep -a GROUND | cut -c1-160
cp export_raw/boss_executioner.glb $T/boss_executioner.pre.glb
python v3_executioner_post.py --pre $T/boss_executioner.pre.glb
npx gltf-transform optimize $T/boss_executioner.pre.glb ../../public/models/boss_executioner.glb --compress meshopt --texture-compress webp   --texture-size ${TEXSIZE:-2048} --flatten false --join false --palette false --instance false --simplify false --prune false 2>&1 | tail -2
python v3_executioner_post.py ../../public/models/boss_executioner.glb
rm -f $T/boss_executioner.pre.glb
python merge_clipmeta.py
python check_soul_glb.py | grep -A4 "boss_executioner"
