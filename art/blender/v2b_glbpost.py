"""建模 B v2：GLB 後處理（系統 Python）。把 P2_／P3_ 節點的 scale 設成 0（預設隱藏），並列出部件、材質、三角面。
用法：python v2b_glbpost.py <file.glb> [--hide]
"""
import json, struct, sys, os


def read(path):
    data = open(path, "rb").read()
    clen, _ = struct.unpack_from("<II", data, 12)
    return json.loads(data[20:20 + clen]), data[20 + clen:]


def write(path, js, rest):
    j = json.dumps(js, separators=(",", ":")).encode("utf-8")
    j += b" " * ((4 - len(j) % 4) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j) + len(rest)))
        f.write(struct.pack("<II", len(j), 0x4E4F534A)); f.write(j); f.write(rest)


path = sys.argv[1]
js, rest = read(path)
if "--hide" in sys.argv:
    for nd in js["nodes"]:
        if (nd.get("name") or "").startswith(("P2_", "P3_")):
            nd["scale"] = [0.0, 0.0, 0.0]
    write(path, js, rest)
    js, rest = read(path)
acc = js["accessors"]
tris = sum(acc[p["indices"]]["count"] // 3 for m in js["meshes"] for p in m["primitives"])
par = {c: i for i, nd in enumerate(js["nodes"]) for c in nd.get("children", [])}
parts = []
for i, nd in enumerate(js["nodes"]):
    n = nd.get("name") or ""
    if n.startswith(("P2_", "P3_")):
        p = par.get(i)
        parts.append(f"{n}(parent={js['nodes'][p]['name'] if p is not None else '-'}, scale={nd.get('scale')})")
print(f"{os.path.basename(path)}: {os.path.getsize(path) / 1048576:.2f} MB tris={tris}")
print(" materials:", [m["name"] for m in js["materials"]])
print(" parts:", parts)
print(" anims:", [a["name"] for a in js.get("animations", [])])
