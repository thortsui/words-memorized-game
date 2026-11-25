// 檢查回合制可愛角色的 GLB：動作名稱齊全、骨頭齊全、三角面數與檔案大小在限制內。
// 用法：node art/blender/check_cute_glb.mjs   （在專案根目錄執行；有任何一項不合格就以非 0 結束）
import { readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const MAX_TRIS = 15000;
const MAX_BYTES = 1024 * 1024;
const BAT_ACTIONS = ["Idle", "Enter", "Attack", "Hit", "Faint", "Victory"];
const BAT_BONES = ["Root", "Body", "Head", "Ear_L", "Ear_R", "Wing1_L", "Wing2_L", "Wing3_L", "Wing1_R", "Wing2_R", "Wing3_R"];
const SPECS = {
  "hero_cute.glb": {
    actions: ["Idle", "Run", "Slash", "Combo", "Cast", "Hit", "Faint", "Victory"],
    bones: ["Root", "Hips", "Spine", "Head", "UpperArm_L", "ForeArm_L", "Hand_L", "UpperArm_R", "ForeArm_R", "Hand_R",
      "Thigh_L", "Shin_L", "Foot_L", "Thigh_R", "Shin_R", "Foot_R", "Sword", "Cape1", "Cape2"],
  },
  "bat_orange.glb": { actions: BAT_ACTIONS, bones: BAT_BONES },
  "bat_shadow.glb": { actions: BAT_ACTIONS, bones: BAT_BONES },
};

function readGlb(path) {
  const buf = readFileSync(path);
  if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error("不是 GLB 檔");
  const jsonLen = buf.readUInt32LE(12);
  return JSON.parse(buf.subarray(20, 20 + jsonLen).toString("utf8"));
}

let failed = false;
for (const [file, spec] of Object.entries(SPECS)) {
  const path = join(root, "public", "models", file);
  const problems = [];
  let gltf;
  try {
    gltf = readGlb(path);
  } catch (e) {
    console.log(`✗ ${file}: 讀取失敗 (${e.message})`);
    failed = true;
    continue;
  }
  const bytes = statSync(path).size;
  let tris = 0;
  let verts = 0;
  for (const mesh of gltf.meshes ?? []) {
    for (const prim of mesh.primitives) {
      if ((prim.mode ?? 4) !== 4) continue;
      const count = prim.indices !== undefined ? gltf.accessors[prim.indices].count : gltf.accessors[prim.attributes.POSITION].count;
      tris += count / 3;
      verts += gltf.accessors[prim.attributes.POSITION].count;
      if (prim.attributes.JOINTS_0 === undefined || prim.attributes.WEIGHTS_0 === undefined) problems.push("有 primitive 沒有蒙皮資料");
    }
  }
  const anims = (gltf.animations ?? []).map((a) => a.name);
  const durations = (gltf.animations ?? []).map((a) => {
    const t = Math.max(...a.samplers.map((s) => gltf.accessors[s.input].max[0]));
    return `${a.name} ${t.toFixed(2)}s`;
  });
  const nodeNames = new Set((gltf.nodes ?? []).map((n) => n.name));
  const joints = new Set((gltf.skins ?? []).flatMap((s) => s.joints.map((j) => gltf.nodes[j].name)));
  for (const a of spec.actions) if (!anims.includes(a)) problems.push(`缺動作 ${a}`);
  for (const a of anims) if (!spec.actions.includes(a)) problems.push(`多餘的動作 ${a}`);
  for (const b of spec.bones) if (!nodeNames.has(b) || !joints.has(b)) problems.push(`缺骨頭 ${b}`);
  if (tris > MAX_TRIS) problems.push(`三角面 ${tris} 超過 ${MAX_TRIS}`);
  if (bytes > MAX_BYTES) problems.push(`檔案 ${bytes} bytes 超過 1 MB`);
  if ((gltf.images ?? []).length) problems.push("不應該有貼圖");
  const ok = problems.length === 0;
  failed ||= !ok;
  console.log(`${ok ? "✓" : "✗"} ${file}: ${tris} tris, ${verts} verts, ${(bytes / 1024).toFixed(0)} KB, ${joints.size} joints, ${(gltf.materials ?? []).length} materials`);
  console.log(`    動作: ${durations.join(", ")}`);
  for (const p of problems) console.log(`    問題: ${p}`);
}
process.exit(failed ? 1 : 0);
