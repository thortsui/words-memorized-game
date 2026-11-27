"""GLB 後處理（系統 Python）：P2_*／P3_* 節點 scale 設 0（預設隱藏）並寫 extras；列出 P2 節點與 Tip_Weapon。
用法：python v2a_post.py [--pre] <file.glb> [...]
  --pre：壓縮前執行。把剛體 P2 節點拆成「P2_X 群組節點（放置位置）＋子節點 P2_X_mesh（掛網格）」，
         因為 gltf-transform 的 meshopt 量化會把反量化縮放寫進掛網格那個節點的 scale；
         scale 0／彈出只能作用在外層群組，否則遊戲端把 scale 設回 1 時網格會變得巨大。
"""
import json, struct, sys


def process(path, pre=False):
    data = bytearray(open(path, "rb").read())
    magic, ver, total = struct.unpack_from("<III", data, 0)
    clen, ctype = struct.unpack_from("<II", data, 12)
    js = json.loads(bytes(data[20:20 + clen]).decode("utf-8"))
    rest = bytes(data[20 + clen:])
    p2 = []
    if pre:
        nodes = js["nodes"]
        for n in list(nodes):
            nm = n.get("name", "")
            if nm.startswith(("P2_", "P3_")) and "mesh" in n and "skin" not in n and not nm.endswith("_mesh"):
                nodes.append({"name": nm + "_mesh", "mesh": n.pop("mesh")})
                n["children"] = n.get("children", []) + [len(nodes) - 1]
                p2.append(nm)
        raw = json.dumps(js, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        raw += b" " * ((4 - len(raw) % 4) % 4)
        open(path, "wb").write(struct.pack("<III", magic, ver, 20 + len(raw) + len(rest)) + struct.pack("<II", len(raw), ctype) + raw + rest)
        print("pre", path, "grouped", p2)
        return
    for n in js.get("nodes", []):
        nm = n.get("name", "")
        if nm.startswith(("P2_", "P3_")) and not nm.endswith("_mesh"):
            ex = n.get("extras", {})
            if "skin" in n:      # 蒙皮網格縮放無效（且 scale 0 會讓 bindMatrix 不可逆）：維持 1，由遊戲端載入時設為不可見
                ex["skinned"] = True
            else:
                n["scale"] = [0.0, 0.0, 0.0]
            ex.update({"form": 3 if nm.startswith("P3_") else 2, "hiddenByDefault": True})
            n["extras"] = ex
            p2.append(nm)
    tip = any(n.get("name") == "Tip_Weapon" for n in js.get("nodes", []))
    raw = json.dumps(js, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    raw += b" " * ((4 - len(raw) % 4) % 4)
    out = struct.pack("<III", magic, ver, 12 + 8 + len(raw) + len(rest)) + struct.pack("<II", len(raw), ctype) + raw + rest
    open(path, "wb").write(out)
    print(f"post {path}: P2 nodes={p2} Tip_Weapon={tip} size={len(out) / 1048576:.2f} MB")


pre = "--pre" in sys.argv
for p in sys.argv[1:]:
    if not p.startswith("--"):
        process(p, pre)
