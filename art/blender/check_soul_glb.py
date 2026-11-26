"""Check the soul-mode GLBs: action names, triangle count, texture sizes, file size, bone names.
usage: python check_soul_glb.py   (system Python; Pillow optional for texture sizes)
"""
import json, struct, os, sys, io
try:
    from PIL import Image
except Exception:
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERO = ["Idle", "Walk", "Slash", "HeavySlash", "Combo", "Roll", "Parry", "Guard", "Hit", "Die", "Victory",
        "Run", "StrafeL", "StrafeR", "DodgeBack", "HitHeavy", "Cast"]
BOSS = ["Idle", "Enter", "Telegraph", "Attack", "Attack2", "Hit", "Stagger", "PhaseShift", "Die",
        "Stalk", "StrafeL", "StrafeR", "IdleAggro", "Combo3", "Delayed", "Dash", "Roar"]
MODELS = {"hero_knight": HERO, "boss_sentinel": BOSS, "boss_executioner": BOSS,
          "boss_gargoyle": BOSS, "boss_priest": BOSS, "boss_devourer": BOSS}
CLIPMETA = json.load(open(os.path.join(ROOT, "src", "battle", "view3d", "clipmeta.json"), encoding="utf-8"))
BONES = ["Root", "Hips", "Spine", "Spine2", "Neck", "Head", "Weapon"] + [b + s for b in
         ("Shoulder", "UpperArm", "Forearm", "Hand", "Thigh", "Shin", "Foot") for s in "LR"]
ok_all = True
for model, need in MODELS.items():
    path = os.path.join(ROOT, "public", "models", model + ".glb")
    if not os.path.exists(path):
        print(model, "MISSING"); ok_all = False; continue
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    clen, ctype = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + clen])
    boff = 20 + clen + 8
    acc = js["accessors"]
    tris = 0; verts = 0
    for m in js["meshes"]:
        for p in m["primitives"]:
            tris += acc[p["indices"]]["count"] // 3
            verts += acc[p["attributes"]["POSITION"]]["count"]
    names = [a["name"] for a in js.get("animations", [])]
    durs = {}
    starts = {}
    for a in js.get("animations", []):
        durs[a["name"]] = max(acc[s["input"]]["max"][0] for s in a["samplers"])
        starts[a["name"]] = min(acc[s["input"]]["min"][0] for s in a["samplers"])
    imgs = []
    for im in js.get("images", []):
        bv = js["bufferViews"][im["bufferView"]]
        raw = data[boff + bv.get("byteOffset", 0): boff + bv.get("byteOffset", 0) + bv["byteLength"]]
        size = Image.open(io.BytesIO(raw)).size if Image else ("?", "?")
        imgs.append((im.get("name", "?"), im.get("mimeType"), size, len(raw) // 1024))
    nodes = {n.get("name") for n in js["nodes"]}
    joints = len(js["skins"][0]["joints"]) if js.get("skins") else 0
    miss = [n for n in need if n not in names]
    extra = [n for n in names if n not in need]
    missb = [b for b in BONES if b not in nodes] if model in ("hero_knight", "boss_sentinel", "boss_executioner") else []   # 生物 Boss 骨架各自不同
    mb = len(data) / 1048576
    big = [i for i in imgs if Image and max(i[2]) > 1024]
    ok = not miss and not extra and not missb and tris <= 30000 and mb <= 3.0 and not big
    ok_all &= ok
    print(f"== {model}: {'OK' if ok else 'FAIL'}  {mb:.2f} MB  tris={tris}  verts={verts}  joints={joints}  materials={[m['name'] for m in js['materials']]}")
    print("   actions:", ", ".join(f"{n}({durs[n]:.2f}s)" for n in names))
    late = {n: round(t, 3) for n, t in starts.items() if t > 1e-4}
    if late:
        print("   片段不是從 0 秒開始:", late); ok = False; ok_all = False
    meta = CLIPMETA.get(model, {})
    bad = {n: (round(durs.get(n, -1), 3), m["dur"]) for n, m in meta.items() if abs(durs.get(n, -1) - m["dur"]) > 0.02}
    if bad:
        print("   clipmeta 時長與 GLB 不符:", bad); ok = False; ok_all = False
    else:
        print(f"   clipmeta: {len(meta)} 片段時長一致；命中:", ", ".join(f"{n}{m['hits']}" for n, m in meta.items() if m.get("hits")))
    if miss or extra or missb:
        print("   missing actions:", miss, "extra:", extra, "missing bones:", missb)
    for i in imgs:
        print(f"   image {i[0]}: {i[1]} {i[2][0]}x{i[2][1]} {i[3]} KB")
print("ALL OK" if ok_all else "SOME FAILED")
sys.exit(0 if ok_all else 1)
