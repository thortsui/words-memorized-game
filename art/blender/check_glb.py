"""檢查匯出的 GLB：動作名稱、三角面數、貼圖尺寸／格式、檔案大小、場景的 FirePoint 節點。
用法：python check_glb.py            （檢查 public/models 內這次交付的 5 個檔）
      python check_glb.py a.glb ...  （只列出資訊，不套規格）
需要 Pillow（讀貼圖尺寸）。任何一項不合規格時 exit code = 1。
"""
import sys, os, json, struct, io

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS = os.path.join(ROOT, "public", "models")
ACTIONS = ["Idle", "Enter", "Telegraph", "Attack", "Attack2", "Hit", "Stagger", "PhaseShift", "Die"]
SPEC = {
    "boss_gargoyle.glb": dict(tris=30000, mb=3.0, tex=1024, actions=ACTIONS, sets=2),
    "boss_priest.glb": dict(tris=30000, mb=3.0, tex=1024, actions=ACTIONS, sets=2),
    "boss_devourer.glb": dict(tris=30000, mb=3.0, tex=1024, actions=ACTIONS, sets=2),
    "arena_cathedral.glb": dict(tris=60000, mb=5.0, tex=1024, actions=[], sets=4, firepoints=4),
    "arena_meadow.glb": dict(tris=60000, mb=5.0, tex=1024, actions=[], sets=4),
}


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, ver, total = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", "不是 GLB"
    off, js, binc = 12, None, b""
    while off < total:
        ln, typ = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + ln]
        if typ == 0x4E4F534A:
            js = json.loads(chunk)
        elif typ == 0x004E4942:
            binc = chunk
        off += 8 + ln
    return js, binc, len(data)


def inspect(path):
    js, binc, size = read_glb(path)
    acc = js.get("accessors", [])
    mesh_tris = []
    for m in js.get("meshes", []):
        t = 0
        for pr in m["primitives"]:
            if pr.get("mode", 4) != 4:
                continue
            n = acc[pr["indices"]]["count"] if "indices" in pr else acc[pr["attributes"]["POSITION"]]["count"]
            t += n // 3
        mesh_tris.append(t)
    tris = sum(mesh_tris[n["mesh"]] for n in js.get("nodes", []) if "mesh" in n)
    verts = sum(acc[pr["attributes"]["POSITION"]]["count"] for m in js.get("meshes", []) for pr in m["primitives"])
    imgs = []
    for im in js.get("images", []):
        bv = js["bufferViews"][im["bufferView"]]
        raw = binc[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        wh = Image.open(io.BytesIO(raw)).size if Image else (0, 0)
        imgs.append(dict(name=im.get("name", "?"), mime=im.get("mimeType", "?"), size=wh, kb=len(raw) / 1024))
    mats = js.get("materials", [])
    texsets = sum(1 for m in mats if "baseColorTexture" in m.get("pbrMetallicRoughness", {}))
    return dict(size=size, tris=tris, verts=verts, images=imgs, texsets=texsets, materials=[m.get("name") for m in mats],
                anims=[(a.get("name"), max(acc[s["input"]]["max"][0] for s in a["samplers"])) for a in js.get("animations", [])],
                joints=sum(len(s["joints"]) for s in js.get("skins", [])),
                nodes=[n.get("name", "") for n in js.get("nodes", [])],
                ext=js.get("extensionsUsed", []))


def main():
    files = sys.argv[1:]
    spec_mode = not files
    if spec_mode:
        files = [os.path.join(MODELS, n) for n in SPEC]
    bad = 0
    for path in files:
        name = os.path.basename(path)
        if not os.path.exists(path):
            print(f"[缺檔] {name}")
            bad += 1
            continue
        r = inspect(path)
        print(f"== {name}: {r['size'] / 1048576:.2f} MB, {r['tris']} tris, {r['verts']} verts, joints {r['joints']}, materials {len(r['materials'])}, 貼圖組 {r['texsets']}")
        for im in r["images"]:
            print(f"   tex {im['name']:<34} {im['mime']:<11} {im['size'][0]}x{im['size'][1]}  {im['kb']:.0f} KB")
        if r["anims"]:
            print("   動作: " + ", ".join(f"{n}({d:.2f}s)" for n, d in r["anims"]))
        fp = [n for n in r["nodes"] if n.startswith("FirePoint")]
        if fp:
            print("   FirePoint 節點: " + ", ".join(fp))
        if r["ext"]:
            print("   extensionsUsed: " + ", ".join(r["ext"]))
        if not spec_mode or name not in SPEC:
            continue
        sp = SPEC[name]
        errs = []
        if r["tris"] > sp["tris"]:
            errs.append(f"三角面 {r['tris']} > {sp['tris']}")
        if r["size"] / 1048576 > sp["mb"]:
            errs.append(f"檔案 {r['size'] / 1048576:.2f} MB > {sp['mb']} MB")
        for im in r["images"]:
            if max(im["size"]) > sp["tex"]:
                errs.append(f"貼圖 {im['name']} {im['size']} 超過 {sp['tex']}")
        if r["texsets"] > sp["sets"]:
            errs.append(f"貼圖組 {r['texsets']} > {sp['sets']}")
        got = [n for n, _ in r["anims"]]
        if sorted(got) != sorted(sp["actions"]):
            errs.append(f"動作不符：缺 {sorted(set(sp['actions']) - set(got))} 多 {sorted(set(got) - set(sp['actions']))}")
        if sp.get("firepoints") and len(fp) < sp["firepoints"]:
            errs.append(f"FirePoint 只有 {len(fp)} 個")
        print("   結果: " + ("OK" if not errs else "不合格 → " + "；".join(errs)))
        bad += bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
