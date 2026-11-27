#!/bin/bash
# 單字魂 v3 主角 hero_knight：建模＋動作＋烘焙＋匯出 → 拼預覽 → 壓縮到 public/models → 合併 clipmeta → 檢查
# 用法：bash art/blender/v3_hero_run.sh [--quick|--nobake|--noanim|--only A,B|--noviews|--tex 2048]
#   帶 --quick／--nobake／--noanim／--only 時只建模＋預覽，不匯出、不動 public/models。
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
TMPD="$(cd ../v3/tmp && pwd -W 2>/dev/null || pwd)/hero"
mkdir -p "$TMPD"
export TEMP="$TMPD" TMP="$TMPD"        # C: 槽快滿：Blender／Cycles 暫存放 D:
"$BL" --background --factory-startup --python v3_hero_build.py -- "$@" > "$TMPD/build.log" 2>&1
grep -E "Error|error|Traceback|File \"|ACTION|reach|TRIS|TOPTRIS|PARTS|ground|BAKED|META|DONE|line [0-9]+" "$TMPD/build.log"
python v3_hero_sheet.py "$TMPD/tiles"
case " $* " in *" --quick "*|*" --nobake "*|*" --noanim "*|*" --only "*) exit 0;; esac
[ -f export_raw/hero_knight.glb ] || { echo "沒有 export_raw/hero_knight.glb"; exit 1; }
(cd ../.. && npx gltf-transform optimize art/blender/export_raw/hero_knight.glb public/models/hero_knight.glb \
   --compress meshopt --texture-compress webp --texture-size 2048 --flatten false --join false --palette false --instance false 2>&1 | tail -2)
ls -la ../../public/models/hero_knight.glb
python merge_clipmeta.py
python check_soul_glb.py | sed -n '1,12p'
