import { defineConfig } from 'vite';
import { readdirSync, statSync } from 'node:fs';
import { resolve } from 'node:path';

// 虛擬模組 virtual:model-list：public/models 裡現有的 .glb 檔名清單。
// 3D 戰鬥畫面只會載入清單裡有的模型，其餘用程式產生的替身，所以不會對不存在的檔案發請求。
// 之後把模型檔放進 public/models，重新 build（開發模式會自動重新整理）就會換成真模型，不必改程式。
function modelList(){const id='virtual:model-list',rid='\0'+id,dir=resolve('public/models');
  return{name:'model-list',
    resolveId:s=>s===id?rid:null,
    load(i){if(i!==rid)return null;let f=[],ver={};try{f=readdirSync(dir).filter(x=>x.endsWith('.glb'));for(const x of f){const s=statSync(resolve(dir,x));ver[x]=s.size+'-'+Math.round(s.mtimeMs)}}catch(e){}
      // 預設匯出仍是檔名陣列；ver＝每個檔的「大小-修改時間」，模型換檔後快取鍵會跟著變
      return`export default Object.assign(${JSON.stringify(f)},{ver:${JSON.stringify(ver)}});`},
    configureServer(server){const hit=p=>{if(!/[\\/]public[\\/]models[\\/]/.test(p))return;const m=server.moduleGraph.getModuleById(rid);if(m)server.moduleGraph.invalidateModule(m);server.ws.send({type:'full-reload'})};
      server.watcher.on('add',hit);server.watcher.on('unlink',hit)}}}

// base './' 讓 GitHub Pages 子路徑也能直接載入
export default defineConfig({ base: './', build: { target: 'es2020', chunkSizeWarningLimit: 900 /* three.js 只在進入戰鬥時才載入 */ }, plugins: [modelList()] });
