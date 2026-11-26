"""把 export_raw/<代號>.clipmeta.json（Blender 匯出時量出的時長、命中時間、是否循環）合併成 src/battle/view3d/clipmeta.json。
用法：python merge_clipmeta.py
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS = ["hero_knight", "boss_sentinel", "boss_gargoyle", "boss_priest", "boss_executioner", "boss_devourer"]
out = {}
for m in MODELS:
    with open(os.path.join(HERE, "export_raw", m + ".clipmeta.json"), encoding="utf-8") as f:
        out[m] = json.load(f)
dst = os.path.join(ROOT, "src", "battle", "view3d", "clipmeta.json")
with open(dst, "w", encoding="utf-8") as f:
    f.write("{\n" + ",\n".join(
        f' "{m}": {{\n' + ",\n".join(f'  "{c}": {json.dumps(v, ensure_ascii=False)}' for c, v in clips.items()) + "\n }"
        for m, clips in out.items()) + "\n}\n")
print("wrote", dst, sum(len(v) for v in out.values()), "clips")
