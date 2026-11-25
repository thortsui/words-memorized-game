// 掃描上傳的端對端測試（Playwright）。這個檔案是一個 async (page)=>{…} 函式，交給 Playwright 的 page 執行：
//   先 npm run dev，用 Playwright 把瀏覽器開到掃描上傳頁（/#upload 或 /tests/scan-harness.html）、調好視窗大小，再呼叫這個函式。
//   想留截圖：先在頁面執行 sessionStorage.setItem('__shot','截圖檔名開頭')。
// 注意：window.__vcScanTamper 只在開發模式（npm run dev）存在，正式建置已移除，所以這支只能對 dev 伺服器跑。
// 流程：上傳 tests/fixtures 的三張合成書頁 → 兩個本機引擎提取 → 核對清單；
//   用 window.__vcScanTamper 故意改錯四筆，檢查它們都被標成需確認、存入被擋下；逐筆確認後才能存入。
async (page) => {
  const vp = page.viewportSize() || { width: 0, height: 0 }, VW = vp.width, VH = vp.height, URL = /^http/.test(page.url()) ? page.url().replace(/#.*$/, '') + (/harness/.test(page.url()) ? '' : '#upload') : 'http://127.0.0.1:5199/tests/scan-harness.html';
  const shot = await page.evaluate(() => sessionStorage.getItem('__shot')).catch(() => null);
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()) });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  // 故意改錯：第 1 頁 fluent 主引擎拼錯一個字母、immediately 複核引擎中文差一個字、opportunity 兩邊都拼錯、複核引擎漏掉 generous
  await page.addInitScript(() => {
    window.__vcScanTamper = (which, list, pi) => { if (pi !== 0) return list; const L = list.map(x => ({ ...x })), f = n => L.find(x => x.en === n);
      if (which === 'a' && f('fluent')) f('fluent').en = 'fluant';
      if (which === 'b' && f('immediately')) f('immediately').zh = '立即；馬上';
      if (f('opportunity')) { const o = f('opportunity'); o.en = 'oportunity'; o.ex = o.ex.replace('opportunity', 'oportunity'); o.blank = 'oportunity'; }
      return which === 'b' ? L.filter(x => x.en !== 'generous') : L; };
  });
  await page.goto(URL);
  await page.evaluate(() => { ['vc-ext', 'vc-ext2', 'vc-adv', 'vc-key'].forEach(k => localStorage.removeItem(k)) });
  await page.reload();
  if (VW) await page.setViewportSize({ width: VW, height: VH });
  await page.waitForSelector('#file', { state: 'attached' });
  const D = 'D:/Documents/ThorWorkSpace/Remamber word game/tests/fixtures/';
  await page.setInputFiles('#file', [D + 'page1.png', D + 'page2.png', D + 'page3.jpg']);
  await page.waitForSelector('#extract');
  const engText = await page.locator('.eng').innerText();
  const keyVisible = await page.locator('#key').count();
  const t0 = Date.now();
  await page.click('#extract');
  await page.waitForSelector('#rev .rc', { timeout: 240000 });
  const extractMs = Date.now() - t0;
  await page.waitForFunction(() => !/核對中/.test(document.querySelector('#revbox').innerText), null, { timeout: 120000 });
  const snap = () => page.evaluate(() => [...document.querySelectorAll('#rev .rc')].map(c => ({ badge: c.querySelector('.badge').textContent, en: c.querySelector('input[data-k=en]').value, zh: c.querySelector('input[data-k=zh]').value, unit: c.querySelector('input[data-k=unit]').value, why: ((c.querySelector('.why') || {}).innerText || '').replace(/\n+/g, ' ¦ '), df: [...c.querySelectorAll('.dfrow')].map(r => r.innerText.replace(/\n+/g, ' / ')), crop: (() => { const cv = c.querySelector('canvas'); return cv ? cv.width + 'x' + cv.height : null })() })));
  const cards = await snap();
  const prog = await page.locator('#prog').innerText(), sum = await page.locator('#vsum').innerText();
  if (shot) { await page.locator('#rev .rc .df').first().scrollIntoViewIfNeeded(); await page.screenshot({ path: shot + '-diff.png' }); await page.evaluate(() => scrollTo(0, 0)); await page.screenshot({ path: shot + '-top.png' }); }
  // 1) 還有未確認的 → 存入必須被擋下
  await page.click('#savebtn'); await page.waitForTimeout(300);
  const blockedToast = await page.locator('#toast').innerText(), stillThere = await page.locator('#rev .rc').count(), dictsAfterBlock = (await page.evaluate(() => window.__dicts ? window.__dicts().length : -1));
  // 2) 選邊：fluant/fluent 那筆點複核引擎的讀法；之後逐筆確認
  const flu = page.locator('#rev .rc', { has: page.locator('input[data-k=en][value="fluant"]') });
  await flu.locator('button[data-pick=b][data-f=en]').click();
  await page.waitForFunction(() => [...document.querySelectorAll('#rev input[data-k=en]')].some(i => i.value === 'fluent'));
  const afterPick = await page.evaluate(() => { const c = [...document.querySelectorAll('#rev .rc')].find(c => c.querySelector('input[data-k=en]').value === 'fluent'); return c.querySelector('.badge').textContent });
  // 取消勾選一筆（兩邊都拼錯的 oportunity），其餘需確認的逐筆按確認
  const opp = page.locator('#rev .rc', { has: page.locator('input[data-k=en][value="oportunity"]') });
  await opp.locator('input[data-k=keep]').uncheck();
  await page.waitForFunction(() => !/核對中/.test(document.querySelector('#revbox').innerText), null, { timeout: 60000 });
  let clicks = 0; for (;;) { const b = page.locator('#rev button[data-a=okd]').first(); if (!(await b.count())) break; await b.scrollIntoViewIfNeeded(); await b.click(); clicks++; if (clicks > 60) break; }
  const sum2 = await page.locator('#vsum').innerText();
  const final = await snap();
  await page.click('#savebtn'); await page.waitForTimeout(400);
  const savedToast = await page.locator('#toast').innerText();
  const dicts = await page.evaluate(() => window.__dicts ? window.__dicts().filter(d => /^單字 /.test(d.name)).map(d => ({ name: d.name, n: d.words.length, words: d.words.map(w => w.en + ' | ' + w.pos + ' | ' + w.zh + ' | ' + w.blank + ' | ' + w.unit) })) : null);
  const overflowX = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth), innerW = await page.evaluate(() => innerWidth);
  return { viewport: VW + 'x' + VH, innerW, url: URL, engText: engText.replace(/\n+/g, ' / '), keyVisible, extractMs, prog, sum, cards: cards.filter(c => c.badge !== '雙重確認').map(c => [c.badge, c.en, c.df.map(d => d.split(' / ')[0]).join('+')].join('｜')), agree: cards.filter(c => c.badge === '雙重確認').length, noCrop: cards.filter(c => !c.crop).length, blockedToast, stillThere, dictsAfterBlock, afterPick, confirmClicks: clicks, sum2, finalBadges: Object.entries(final.reduce((t, c) => (t[c.badge] = (t[c.badge] || 0) + 1, t), {})).map(x => x.join(' ')).join('、'), savedToast, dicts: dicts && dicts.slice(-1).map(d => ({ name: d.name, n: d.words.length, hasFluent: d.words.some(w => w.startsWith('fluent |')), hasFluant: d.words.some(w => w.startsWith('fluant')), hasOportunity: d.words.some(w => w.startsWith('oportunity')) })), overflowX, errors };
}
