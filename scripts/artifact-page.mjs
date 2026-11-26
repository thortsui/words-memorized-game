// 產生給 claude.ai Artifact 發布用的版本（dist-claude/）。
// Artifact 不提供 .glb 檔型，所以模型轉成 base64 文字檔；首頁只留 <title>、樣式、腳本與 body（Artifact 會自己包 <html><head><body>）。
// 用法：node scripts/artifact-page.mjs   （會自己建置）
import { readFileSync, writeFileSync, readdirSync, unlinkSync } from 'node:fs';
import { execSync } from 'node:child_process';
const OUT = 'dist-claude';
execSync(`npx vite build --outDir ${OUT} --emptyOutDir`, { stdio: 'inherit', env: { ...process.env, VITE_GLB_B64: '1' } });
for (const f of readdirSync(`${OUT}/models`)) if (f.endsWith('.glb')) {
  writeFileSync(`${OUT}/models/${f}.b64.txt`, readFileSync(`${OUT}/models/${f}`).toString('base64'));
  unlinkSync(`${OUT}/models/${f}`);
}
const src = readFileSync(`${OUT}/index.html`, 'utf8');
const head = src.match(/<head>([\s\S]*?)<\/head>/)[1], body = src.match(/<body>([\s\S]*?)<\/body>/)[1];
const keep = head.split('\n').filter(l => /<title>|fonts\.googleapis\.com\/css2|<script |rel="stylesheet"/.test(l)).map(l => l.trim());
writeFileSync(`${OUT}/claude.html`, keep.join('\n') + '\n' + body.trim() + '\n');
unlinkSync(`${OUT}/index.html`);
const list = (d, p = '') => readdirSync(d, { withFileTypes: true }).flatMap(e => e.isDirectory() ? list(`${d}/${e.name}`, p + e.name + '/') : [p + e.name]);
console.log(JSON.stringify(Object.fromEntries(list(OUT).filter(f => f !== 'claude.html').map(f => [f, f]))));
