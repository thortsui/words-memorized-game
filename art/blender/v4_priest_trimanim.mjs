// v1.3.0 霜冠祭司：壓縮前移除「無作用」的動畫通道（gltf-transform optimize 之前執行）。
// Blender 強制取樣會替每根骨頭在每個片段都寫 translation／rotation／scale 三條通道（129 條／片段）。
// 除了 Hips 位移之外，所有骨頭的 translation 與 scale 在每一格都等於骨頭本身的靜止值，播放時沒有任何作用，
// 卻讓 GLB 的 JSON（每條通道一組 accessor＋min/max）和資料多出好幾百 KB；新增 5 個招式後超過 4.5 MB。
// 這裡只刪「整段都等於該節點靜止值（誤差 1e-5）」的通道：既然值永遠是靜止值，刪掉後畫面完全一樣
// （three.js 沒有軌道的骨頭維持節點靜止值，且所有片段都一樣，交叉淡入也不受影響）。旋轉通道一律保留。
// 用法：node v4_priest_trimanim.mjs <in.glb> [out.glb]
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { prune } from '@gltf-transform/functions';

const [, , IN, OUT = IN] = process.argv;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(IN);
const EPS = 1e-5;
let removed = 0, kept = 0;
// 同一節點同一路徑：只要有任何片段不是靜止值就整組保留（保險：不讓某片段的值殘留到另一片段）
const varying = new Set();
const chans = [];
for (const anim of doc.getRoot().listAnimations()) {
  for (const ch of anim.listChannels()) {
    const path = ch.getTargetPath();
    const node = ch.getTargetNode();
    if (!node || (path !== 'translation' && path !== 'scale')) { kept++; continue; }
    const rest = path === 'translation' ? node.getTranslation() : node.getScale();
    const arr = ch.getSampler().getOutput().getArray();
    let same = true;
    for (let i = 0; i < arr.length && same; i++) if (Math.abs(arr[i] - rest[i % 3]) > EPS) same = false;
    const key = node.getName() + '|' + path;
    if (!same) varying.add(key);
    chans.push({ anim, ch, key });
  }
}
for (const { anim, ch, key } of chans) {
  if (varying.has(key)) { kept++; continue; }
  const s = ch.getSampler();
  anim.removeChannel(ch); ch.dispose();
  if (!anim.listChannels().some((c) => c.getSampler() === s)) { anim.removeSampler(s); s.dispose(); }
  removed++;
}
await doc.transform(prune({ propertyTypes: ['accessor'], keepLeaves: false }));
await io.write(OUT, doc);
console.log(`trimanim: removed ${removed} no-op channels, kept ${kept}; varying node paths: ${[...varying].join(', ')}`);
