#!/bin/bash
# 第二版動畫：重新產生動作（沿用已烘焙貼圖）、匯出未壓縮 GLB 到 export_raw/、壓縮到 public/models/、拼 preview/anim2 預覽。
# 用法：bash run_anim2.sh <hero|sentinel|executioner|gargoyle|priest|devourer>
cd "$(dirname "$0")"
BL="/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
case "$1" in
  hero) M=hero_knight; S="build_soul_hero.py -- --nobake --noviews";;
  sentinel) M=boss_sentinel; S="build_soul_sentinel.py -- --nobake --noviews";;
  executioner) M=boss_executioner; S="build_soul_executioner.py -- --nobake --noviews";;
  gargoyle|priest|devourer) M=boss_$1; S="build_boss_$1.py -- anim2";;
esac
mkdir -p preview/anim2 export_raw
rm -f preview/_tiles/$M/act_* preview/_tiles/$M/strip_* preview/_frames/${M}__*
"$BL" --background --factory-startup --python $S 2>&1 | grep -E "Error|error|Traceback|File \"|ACTION|ground|DONE|META|\[export|line [0-9]+"
if ls preview/_tiles/$M/act_* >/dev/null 2>&1; then python soul_sheet.py preview/_tiles/$M preview/anim2 $M; rm -f preview/anim2/${M}_views.jpg preview/anim2/${M}_closeup.jpg; fi
if ls preview/_frames/${M}__* >/dev/null 2>&1; then python make_sheet.py actions preview/anim2/${M}_actions.jpg preview/_frames $M "$(python -c "import json;print(','.join(json.load(open('export_raw/$M.clipmeta.json'))))")"; fi
npx --yes gltf-transform optimize export_raw/$M.glb ../../public/models/$M.glb --compress meshopt --texture-compress webp --texture-size 1024 2>&1 | tail -3
ls -la export_raw/$M.glb ../../public/models/$M.glb
