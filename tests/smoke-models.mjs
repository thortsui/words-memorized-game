// 冒煙測試：兩種戰鬥各開一場，確認壓縮後的模型載得進來、沒有錯誤。用法：先 vite preview --port 4190，再 node tests/smoke-models.mjs
import { chromium } from 'playwright-core';
const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
let bad = 0;
for (const game of [true, 'soul']) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 700 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true });
  const p = await ctx.newPage();
  const logs = [], glb = [];
  p.on('console', m => { if (['error', 'warning'].includes(m.type())) logs.push(m.type() + ': ' + m.text().slice(0, 200)); });
  p.on('pageerror', e => logs.push('pageerror: ' + e.message.slice(0, 200)));
  p.on('response', r => { if (r.status() >= 400) logs.push('HTTP ' + r.status() + ' ' + r.url()); if (r.url().includes('.glb')) glb.push(r.url().split('/').pop() + ' ' + r.status()); });
  await p.addInitScript(g => {
    localStorage.setItem('vc-setup', JSON.stringify({ dict: 'no307', mode: 'en2zh', scope: 'all', n: 10, wrong: false, auto: false, exmode: false, game: g }));
    localStorage.setItem('vc-story', '1'); localStorage.setItem('vc-story-soul', '1'); localStorage.setItem('vc-bgm', '0');
  }, game);
  await p.goto((process.env.SMOKE_URL||'http://127.0.0.1:4190/')+'#practice');
  await p.locator('#start').click();
  await p.waitForTimeout(14000);
  const a = await p.evaluate(() => { const e = document.querySelector('#arena'); return e ? { fps: e.dataset.fps, q: e.dataset.quality, canvas: !!e.querySelector('canvas'), text: document.body.innerText.slice(0, 120).replace(/\n/g, ' ') } : null; });
  await p.screenshot({ path: `tests/smoke-${game === true ? 'monster' : 'soul'}.png` });
  console.log(game === true ? 'monster' : 'soul', JSON.stringify(a), '\n  glb:', glb.join(', '), '\n  logs:', logs.length ? logs.join(' | ') : 'none');
  if (logs.filter(l => !/favicon|Failed to load resource/.test(l)).length || !a || !a.canvas || glb.length < 3) bad++;
  await ctx.close();
}
await b.close();
process.exit(bad ? 1 : 0);
