"""v3 暗影行刑者 GLB 後處理（由 v3_devourer_post.py 複製）（系統 Python）。
  --pre ：壓縮前。剛體 P2_／P3_ 拆成「群組節點 P*_X（scale 0、掛骨）＋子節點（掛網格）」——
          gltf-transform 的 meshopt 量化會把反量化縮放寫進掛網格那個節點的 scale，scale 0／彈出只能作用在外層群組。
          子節點一般命名 P*_X_mesh；三階要一起消失的二階部件（紙翼、胸口巨口：參考圖三階沒有）子節點命名 X3_P*_X，
          phaseShow 在三階會把 X3_* 設成不可見。
  預設  ：壓縮後。P2_／P3_ 群組節點 scale 設 0，寫 extras；列出節點、材質、三角面。
用法：python v3_executioner_post.py [--pre] <file.glb>
"""
import json, struct, sys, os

HIDE_IN_P3 = ()   # 行刑者沒有三階


def rd(path):
    data = open(path, "rb").read()
    clen, = struct.unpack_from("<I", data, 12)
    return json.loads(data[20:20 + clen]), data[20 + clen:]


def wr(path, js, rest):
    j = json.dumps(js, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    j += b" " * ((4 - len(j) % 4) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j) + len(rest)))
        f.write(struct.pack("<II", len(j), 0x4E4F534A)); f.write(j); f.write(rest)


path = [a for a in sys.argv[1:] if not a.startswith("--")][0]
js, rest = rd(path)
nodes = js["nodes"]
if "--pre" in sys.argv:
    g = []
    for n in list(nodes):
        nm = n.get("name", "")
        if nm.startswith(("P2_", "P3_")) and "mesh" in n and "skin" not in n:
            child = ("X3_" + nm) if nm in HIDE_IN_P3 else nm + "_mesh"
            nodes.append({"name": child, "mesh": n.pop("mesh")})
            n["children"] = n.get("children", []) + [len(nodes) - 1]
            g.append(nm)
    wr(path, js, rest)
    print("pre grouped", g)
    sys.exit(0)
for n in nodes:
    nm = n.get("name", "")
    if nm.startswith(("P2_", "P3_")) and "mesh" not in n:
        n["scale"] = [0.0, 0.0, 0.0]
        ex = n.get("extras", {}); ex.update({"form": 3 if nm.startswith("P3_") else 2, "hiddenByDefault": True}); n["extras"] = ex
wr(path, js, rest)
js, rest = rd(path)
acc = js["accessors"]
tris = sum(acc[p["indices"]]["count"] // 3 for m in js["meshes"] for p in m["primitives"])
par = {c: i for i, nd in enumerate(js["nodes"]) for c in nd.get("children", [])}
print(f"{os.path.basename(path)}: {os.path.getsize(path) / 1048576:.2f} MB tris={tris}")
print(" materials:", [m["name"] for m in js["materials"]])
print(" P nodes:", [f"{nd['name']}<{js['nodes'][par[i]]['name'] if i in par else '-'}>s={nd.get('scale')}" for i, nd in enumerate(js["nodes"]) if nd.get("name", "").startswith(("P2_", "P3_")) and not nd["name"].endswith("_mesh")])
print(" X3 nodes:", [nd["name"] for nd in js["nodes"] if nd.get("name", "").startswith("X3_")])
print(" Tip_Weapon:", any(nd.get("name") == "Tip_Weapon" for nd in js["nodes"]))
print(" anims:", [a["name"] for a in js.get("animations", [])])
