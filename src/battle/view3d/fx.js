// 特效：粒子（Points，一次 draw call）、DOM 浮字（傷害數字／擬聲字）、斬痕、衝擊環、閃光、閃電、光柱、魔法陣、殘影。
// 所有特效都用引擎的遊戲時間，setTimeScale 與頓格會一起影響。
// v2（特效，魂系）：「墨與鏽」語彙——粒子多了一張 4×4 圖集（原創符字、墨滴、墨潑、金箔、筆觸、書頁、星芒、灰燼、小圓相），
// 魂系的 fx.slash 改成筆刷刀光（頭粗尾細、飛白、墨色底層＋加色主色），另有 brush／enso／seal／decal／inkVeil／afterimage。
// 粒子數受 eng.fxK（vfx2.js 依 FPS 調整，低效能 ×0.5）與池預算（加色 500／一般 300／條紋 160）限制；打怪模式行為不變。
import * as THREE from 'three';
import { clone as skClone } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { ease, lerp, rand } from './engine.js';

const V=p=>p&&p.isVector3?p:new THREE.Vector3(p[0],p[1],p[2]);
const pick=c=>Array.isArray(c)?c[(Math.random()*c.length)|0]:c;
// 圖集粒子 kind（4 起）：見 atlasTexture()
export const K={glyph:[4,5,6,7,8,9,10,11],drop:12,splat:13,leaf:14,dab:15,page:16,star:17,ash:18,ringdab:19};

/* ---------- 粒子池 ---------- */
const VS=`attribute float size;attribute vec4 pcolor;attribute float kind;varying vec4 vC;varying float vK;uniform float uScale;
void main(){vC=pcolor;vK=kind;vec4 mv=modelViewMatrix*vec4(position,1.);gl_PointSize=size*uScale/max(.1,-mv.z);gl_Position=projectionMatrix*mv;}`;
// kind 0：柔邊圓點　1：四角星芒　2：實心圓（彩帶、花瓣）　3：愛心（回血招式）
// kind 4–19：圖集格子（kind 的小數部分＝這顆粒子的旋轉角），圖集 RGB 會乘上粒子顏色（書頁的格線、金箔的明暗）
const FS=`varying vec4 vC;varying float vK;uniform sampler2D uAtlas;
void main(){vec2 p=gl_PointCoord-.5;float d=length(p);float a;vec3 tint=vec3(1.);
 if(vK<.5){a=smoothstep(.5,.08,d);}
 else if(vK<1.5){float s=abs(p.x)*abs(p.y)*90.;a=max(0.,1.-s)*smoothstep(.5,.2,d);a=max(a,smoothstep(.16,.0,d));}
 else if(vK<2.5){a=step(d,.42);}
 else if(vK<3.9){vec2 q=vec2(p.x*2.7,.08-p.y*2.7);float u=q.x*q.x+q.y*q.y-1.;float f=u*u*u-q.x*q.x*q.y*q.y*q.y;a=1.-smoothstep(-.03,.03,f);}
 else{float c=floor(vK-4.+.001);float r=fract(vK)*6.2832;vec2 q=vec2(cos(r)*p.x-sin(r)*p.y,sin(r)*p.x+cos(r)*p.y)*1.08+.5;
  if(q.x<0.||q.x>1.||q.y<0.||q.y>1.)discard;vec4 t=texture2D(uAtlas,(vec2(mod(c,4.),3.-floor(c/4.))+vec2(q.x,1.-q.y))*.25);a=t.a;tint=t.rgb;}
 if(a<.01)discard;gl_FragColor=vec4(vC.rgb*tint,vC.a*a);}`;

function makePool(eng,max,additive,budget=max){
  const pos=new Float32Array(max*3),col=new Float32Array(max*4),size=new Float32Array(max),kind=new Float32Array(max);
  const vel=new Float32Array(max*3),life=new Float32Array(max),maxLife=new Float32Array(max),grav=new Float32Array(max),drag=new Float32Array(max),size0=new Float32Array(max),a0=new Float32Array(max),grow=new Float32Array(max);
  const g=new THREE.BufferGeometry();
  g.setAttribute("position",new THREE.BufferAttribute(pos,3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute("pcolor",new THREE.BufferAttribute(col,4).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute("size",new THREE.BufferAttribute(size,1).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute("kind",new THREE.BufferAttribute(kind,1).setUsage(THREE.DynamicDrawUsage));
  const m=new THREE.ShaderMaterial({vertexShader:VS,fragmentShader:FS,uniforms:{uScale:{value:300},uAtlas:{value:null}},transparent:true,depthWrite:false,blending:additive?THREE.AdditiveBlending:THREE.NormalBlending});
  const pts=new THREE.Points(g,m);pts.frustumCulled=false;pts.renderOrder=additive?11:10;eng.scene.add(pts);
  let cur=0,alive=0,dirty=false;const c=new THREE.Color();
  function emit(o){let n=o.n||1;if(eng.rm)n=Math.ceil(n*.4);else if(eng.quality==="low"){if(o.deco)return;n=Math.ceil(n*.35)} // 低畫質：裝飾用的粒子（花粉、飄雪）不發，其餘約三分之一
    // 特效預算：vfx2 的掉幀降級（eng.fxK）＋同時存活數超過預算時減半（裝飾粒子直接不發）
    if(eng.fxK!=null&&eng.fxK<1){if(o.deco&&eng.fxK<.6)return;n=n*eng.fxK}
    if(alive>budget*.85){if(o.deco)return;n=n*(alive>budget?.35:.6)}
    if(n<1){if(Math.random()<n)n=1;else return}n=Math.round(n);
    dirty=true;
    const p=V(o.p),sp=o.speed||[.5,1.5],sz=o.size||[.08,.16],lf=o.life||[.4,.8],dir=o.dir?V(o.dir):null,spread=o.spread==null?1:o.spread,rad=o.radius||0;
    for(let i=0;i<n;i++){const k=cur;cur=(cur+1)%max;
      // 方向：有 dir 就在它周圍散開，沒有就是全向
      let dx=rand(-1,1),dy=rand(-1,1),dz=rand(-1,1);const l=Math.hypot(dx,dy,dz)||1;dx/=l;dy/=l;dz/=l;
      if(dir){dx=dir.x+dx*spread;dy=dir.y+dy*spread;dz=dir.z+dz*spread;const l2=Math.hypot(dx,dy,dz)||1;dx/=l2;dy/=l2;dz/=l2}
      if(o.flat!=null)dy*=o.flat;
      const s=rand(sp[0],sp[1]);vel[k*3]=dx*s;vel[k*3+1]=dy*s+(o.up||0);vel[k*3+2]=dz*s;
      pos[k*3]=p.x+rand(-rad,rad);pos[k*3+1]=p.y+rand(-rad,rad)*(o.radiusY==null?1:o.radiusY);pos[k*3+2]=p.z+rand(-rad,rad);
      c.set(pick(o.color||0xffffff));col[k*4]=c.r;col[k*4+1]=c.g;col[k*4+2]=c.b;col[k*4+3]=0;
      a0[k]=(o.alpha==null?1:o.alpha)*(additive&&eng._soulFx&&n>=30?.55:1); // 魂系：同一點爆出大量加色粒子時壓低亮度，避免糊成光球
size0[k]=rand(sz[0],sz[1]);size[k]=size0[k];grow[k]=o.grow||0;
      maxLife[k]=life[k]=rand(lf[0],lf[1]);grav[k]=o.gravity||0;drag[k]=o.drag||0;let kd=pick(o.kind)||0;if(kd>=4)kd=Math.floor(kd)+(o.norot?0:Math.random()*.98);kind[k]=kd}
    g.attributes.kind.needsUpdate=true}
  function update(dt){if(dt<=0)return;if(!alive&&!dirty)return; // 沒有粒子時不必每幀掃一遍、重傳三個緩衝
    alive=0;dirty=false;
    for(let k=0;k<max;k++){if(life[k]<=0)continue;life[k]-=dt;
      if(life[k]<=0){col[k*4+3]=0;size[k]=0;continue}alive++;
      const d=Math.max(0,1-drag[k]*dt);vel[k*3]*=d;vel[k*3+1]=vel[k*3+1]*d-grav[k]*dt;vel[k*3+2]*=d;
      pos[k*3]+=vel[k*3]*dt;pos[k*3+1]+=vel[k*3+1]*dt;pos[k*3+2]+=vel[k*3+2]*dt;
      const r=life[k]/maxLife[k]; // 1 → 0
      col[k*4+3]=a0[k]*Math.min(1,r*2.2)*Math.min(1,(1-r)*8);size[k]=size0[k]*(1+grow[k]*(1-r))}
    g.attributes.position.needsUpdate=true;g.attributes.pcolor.needsUpdate=true;g.attributes.size.needsUpdate=true}
  return{emit,update,pts,mat:m,get alive(){return alive}};
}

/* ---------- 火花條（金屬撞擊）：沿速度方向拉長、面向鏡頭的細長四邊形，頭亮尾暗；顏色乘上 HDR 倍率讓光暈吃得到 ---------- */
function makeStreaks(eng,max,budget=max){
  const pos=new Float32Array(max*12),col=new Float32Array(max*12),idx=new Uint16Array(max*6);
  for(let i=0;i<max;i++){const v=i*4;idx.set([v,v+1,v+2,v+1,v+3,v+2],i*6)}
  const P=new Float32Array(max*3),Vl=new Float32Array(max*3),life=new Float32Array(max),ml=new Float32Array(max),C=new Float32Array(max*3),W=new Float32Array(max),L=new Float32Array(max),Gr=new Float32Array(max),Dr=new Float32Array(max);
  const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3).setUsage(THREE.DynamicDrawUsage));g.setAttribute("color",new THREE.BufferAttribute(col,3).setUsage(THREE.DynamicDrawUsage));g.setIndex(new THREE.BufferAttribute(idx,1));
  const m=new THREE.MeshBasicMaterial({vertexColors:true,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide,fog:false,toneMapped:false});
  const mesh=new THREE.Mesh(g,m);mesh.frustumCulled=false;mesh.renderOrder=12;eng.scene.add(mesh);
  let cur=0,alive=0;const c=new THREE.Color(),cam=new THREE.Vector3(),h=new THREE.Vector3(),t=new THREE.Vector3(),d=new THREE.Vector3(),sd=new THREE.Vector3();
  // o：{p, n, color, speed:[a,b], dir, spread, up, life:[a,b], gravity, drag, width, len（拖尾秒數）, hdr（亮度倍率）}
  function emit(o){let n=o.n||10;if(eng.rm)n=Math.ceil(n*.4);else if(eng.quality==="low")n=Math.ceil(n*.4);
    if(eng.fxK!=null&&eng.fxK<1)n=Math.ceil(n*eng.fxK);if(alive>budget*.85)n=Math.ceil(n*(alive>budget?.3:.6));
    const p=V(o.p),sp=o.speed||[4,12],lf=o.life||[.18,.45],dir=o.dir?V(o.dir):null,spread=o.spread==null?1:o.spread,hdr=Math.min(o.hdr||3,eng._soulFx?1.7:99); // 魂系：一團火花太亮會被泛光糊成一大片光球（2.4 時終結一刀的 70＋26 條火花在近景仍會變成蓋住主角的光球，改 1.7、單次最多 40 條）
    if(eng._soulFx)n=Math.min(n,40);
    for(let i=0;i<n;i++){const k=cur;cur=(cur+1)%max;let dx=rand(-1,1),dy=rand(-.6,1),dz=rand(-1,1);const l=Math.hypot(dx,dy,dz)||1;dx/=l;dy/=l;dz/=l;
      if(dir){dx=dir.x+dx*spread;dy=dir.y+dy*spread;dz=dir.z+dz*spread;const l2=Math.hypot(dx,dy,dz)||1;dx/=l2;dy/=l2;dz/=l2}
      const s=rand(sp[0],sp[1]);Vl[k*3]=dx*s;Vl[k*3+1]=dy*s+(o.up||0);Vl[k*3+2]=dz*s;P[k*3]=p.x;P[k*3+1]=p.y;P[k*3+2]=p.z;
      c.set(pick(o.color||[0xfff2c0,0xffc060,0xffffff]));const b=hdr*rand(.7,1.2);C[k*3]=c.r*b;C[k*3+1]=c.g*b;C[k*3+2]=c.b*b;
      W[k]=(o.width||.022)*rand(.7,1.3);L[k]=(o.len||.045)*rand(.7,1.4);Gr[k]=o.gravity==null?11:o.gravity;Dr[k]=o.drag==null?1.6:o.drag;ml[k]=life[k]=rand(lf[0],lf[1])}
    alive=Math.max(alive,1)}
  function update(dt){if(!alive)return;if(dt<=0)return;alive=0;eng.camera.getWorldPosition(cam);
    for(let k=0;k<max;k++){const o=k*12;if(life[k]<=0){if(col[o]||col[o+3]){col.fill(0,o,o+12);pos.fill(0,o,o+12)}continue}
      life[k]-=dt;if(life[k]<=0){col.fill(0,o,o+12);pos.fill(0,o,o+12);continue}alive++;
      const dk=Math.max(0,1-Dr[k]*dt);Vl[k*3]*=dk;Vl[k*3+1]=Vl[k*3+1]*dk-Gr[k]*dt;Vl[k*3+2]*=dk;
      P[k*3]+=Vl[k*3]*dt;P[k*3+1]+=Vl[k*3+1]*dt;P[k*3+2]+=Vl[k*3+2]*dt;
      h.set(P[k*3],P[k*3+1],P[k*3+2]);d.set(Vl[k*3],Vl[k*3+1],Vl[k*3+2]);t.copy(h).addScaledVector(d,-L[k]);
      // 寬度方向＝速度 × 視線，四邊形永遠正對鏡頭
      sd.subVectors(cam,h).cross(d);const sl=sd.length();if(sl<1e-6)sd.set(W[k],0,0);else sd.multiplyScalar(W[k]/sl);
      const r=life[k]/ml[k],f=Math.min(1,r*1.6),hr=C[k*3]*f,hg=C[k*3+1]*f,hb=C[k*3+2]*f;
      pos[o]=h.x-sd.x;pos[o+1]=h.y-sd.y;pos[o+2]=h.z-sd.z;pos[o+3]=h.x+sd.x;pos[o+4]=h.y+sd.y;pos[o+5]=h.z+sd.z;
      pos[o+6]=t.x-sd.x*.3;pos[o+7]=t.y-sd.y*.3;pos[o+8]=t.z-sd.z*.3;pos[o+9]=t.x+sd.x*.3;pos[o+10]=t.y+sd.y*.3;pos[o+11]=t.z+sd.z*.3;
      col[o]=col[o+3]=hr;col[o+1]=col[o+4]=hg;col[o+2]=col[o+5]=hb;col[o+6]=col[o+9]=hr*.12;col[o+7]=col[o+10]=hg*.08;col[o+8]=col[o+11]=hb*.04}
    g.attributes.position.needsUpdate=true;g.attributes.color.needsUpdate=true}
  return{emit,update,mesh,get alive(){return alive}}}

/* ---------- 共用貼圖 ---------- */
function glowTexture(){const c=document.createElement("canvas");c.width=c.height=64;const x=c.getContext("2d");const g=x.createRadialGradient(32,32,0,32,32,32);
  g.addColorStop(0,"rgba(255,255,255,1)");g.addColorStop(.25,"rgba(255,255,255,.75)");g.addColorStop(.6,"rgba(255,255,255,.18)");g.addColorStop(1,"rgba(255,255,255,0)");x.fillStyle=g;x.fillRect(0,0,64,64);
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t}
function blobTexture(){const c=document.createElement("canvas");c.width=c.height=64;const x=c.getContext("2d");const g=x.createRadialGradient(32,32,2,32,32,32);
  g.addColorStop(0,"rgba(255,255,255,.62)");g.addColorStop(.55,"rgba(255,255,255,.38)");g.addColorStop(1,"rgba(255,255,255,0)");x.fillStyle=g;x.fillRect(0,0,64,64);return new THREE.CanvasTexture(c)}
// 魔法陣：雙圈、六芒星與刻度（白色，顏色由材質決定）
function circleTexture(){const S=256,c=document.createElement("canvas");c.width=c.height=S;const x=c.getContext("2d");x.translate(S/2,S/2);x.strokeStyle="#fff";x.lineCap="round";
  x.lineWidth=5;x.beginPath();x.arc(0,0,120,0,7);x.stroke();x.lineWidth=2.5;x.beginPath();x.arc(0,0,104,0,7);x.stroke();x.beginPath();x.arc(0,0,58,0,7);x.stroke();
  x.lineWidth=3.5;for(let k=0;k<2;k++){x.beginPath();for(let i=0;i<3;i++){const a=k*Math.PI/3+i*Math.PI*2/3-Math.PI/2;x[i?"lineTo":"moveTo"](Math.cos(a)*104,Math.sin(a)*104)}x.closePath();x.stroke()}
  x.lineWidth=3;for(let i=0;i<24;i++){const a=i*Math.PI/12;x.beginPath();x.moveTo(Math.cos(a)*108,Math.sin(a)*108);x.lineTo(Math.cos(a)*(i%2?114:118),Math.sin(a)*(i%2?114:118));x.stroke()}
  for(let i=0;i<6;i++){const a=i*Math.PI/3+Math.PI/6;x.beginPath();x.arc(Math.cos(a)*81,Math.sin(a)*81,7,0,7);x.stroke()}
  return new THREE.CanvasTexture(c)}

// 光柱用的上下漸層：底部最亮、往上淡出，底端也收掉硬邊
function beamTexture(){const c=document.createElement("canvas");c.width=4;c.height=128;const x=c.getContext("2d"),g=x.createLinearGradient(0,128,0,0);
  g.addColorStop(0,"rgba(255,255,255,0)");g.addColorStop(.06,"rgba(255,255,255,1)");g.addColorStop(.35,"rgba(255,255,255,.55)");g.addColorStop(1,"rgba(255,255,255,0)");x.fillStyle=g;x.fillRect(0,0,4,128);return new THREE.CanvasTexture(c)}

/* ---------- v2 水墨貼圖（canvas 產生，全部 ≤ 256²） ---------- */
// 固定種子的亂數：每次產生的符字都一樣（原創筆畫組合，不是可讀的真實文字）
function rng(s){return()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
const cv=S=>{const c=document.createElement("canvas");c.width=c.height=S;return c};
// 頭粗尾細的一筆：用一串圓點疊出來（w0 起筆寬、w1 收筆寬）
function stroke(x,pts,w0,w1,n=18){for(let s=0;s<=n;s++){const u=s/n;let px,py;if(pts.length===2){px=pts[0][0]+(pts[1][0]-pts[0][0])*u;py=pts[0][1]+(pts[1][1]-pts[0][1])*u}
  else{const a=pts[0],b=pts[1],c=pts[2];px=(1-u)*(1-u)*a[0]+2*(1-u)*u*b[0]+u*u*c[0];py=(1-u)*(1-u)*a[1]+2*(1-u)*u*b[1]+u*u*c[1]}
  x.beginPath();x.arc(px,py,Math.max(.4,w0+(w1-w0)*u),0,7);x.fill()}}
// 4×4 圖集，每格 64px：0–7 原創符字、8 墨滴、9 墨潑、10 金箔、11 筆觸、12 書頁、13 星芒、14 灰燼、15 小圓相
function atlasTexture(){const S=256,C=64,c=cv(S),x=c.getContext("2d");
  const cell=(i,f)=>{x.save();x.translate((i%4)*C,Math.floor(i/4)*C);x.beginPath();x.rect(0,0,C,C);x.clip();x.fillStyle="#fff";x.strokeStyle="#fff";x.lineCap="round";f();x.restore()};
  for(let g=0;g<8;g++)cell(g,()=>{const r=rng(17+g*31),N=3+Math.floor(r()*3);
    for(let k=0;k<N;k++){const t=r(),x0=14+r()*34,y0=12+r()*30;
      if(t<.3)stroke(x,[[x0,y0],[Math.min(54,x0+16+r()*18),y0+(r()-.5)*7]],4.2,1.6);
      else if(t<.58)stroke(x,[[x0,y0],[x0+(r()-.5)*5,Math.min(56,y0+16+r()*20)]],4.4,1.4);
      else if(t<.82)stroke(x,[[x0,y0],[x0-6,y0+10],[Math.max(8,x0-16-r()*8),Math.min(56,y0+18+r()*8)]],4,1);
      else{x.beginPath();x.arc(x0,y0,3.2+r()*1.6,0,7);x.fill()}}});
  cell(8,()=>{x.beginPath();x.arc(32,38,13,0,7);x.fill();x.beginPath();x.moveTo(20,34);x.quadraticCurveTo(30,18,32,6);x.quadraticCurveTo(34,18,44,34);x.fill();x.beginPath();x.arc(50,52,4,0,7);x.fill()});
  cell(9,()=>{const r=rng(5);x.beginPath();for(let i=0;i<=30;i++){const a=i/30*6.283,rr=15*(1+.25*Math.sin(a*3+1)+.18*Math.sin(a*7)+.14*(r()-.5));x[i?"lineTo":"moveTo"](32+Math.cos(a)*rr,32+Math.sin(a)*rr)}x.fill();
    for(let i=0;i<9;i++){const a=r()*6.283,d=19+r()*10;x.beginPath();x.arc(32+Math.cos(a)*d,32+Math.sin(a)*d,1.2+r()*3,0,7);x.fill()}});
  cell(10,()=>{const r=rng(9);x.beginPath();const n=6;for(let i=0;i<=n;i++){const a=i/n*6.283+r()*.5,rr=14+r()*12;x[i?"lineTo":"moveTo"](32+Math.cos(a)*rr,32+Math.sin(a)*rr*.8)}x.fill();
    x.globalCompositeOperation="source-atop";for(let i=0;i<4;i++){x.beginPath();x.moveTo(10+r()*44,6);x.lineTo(14+r()*40,58);x.lineWidth=2+r()*4;x.strokeStyle="#9a9a9a";x.stroke()}});
  cell(11,()=>{const r=rng(3);for(let i=0;i<22;i++){const y=22+r()*20,x0=6+r()*10,x1=46+r()*12,w=.8+r()*1.8;x.globalAlpha=.4+r()*.6;x.lineWidth=w;x.beginPath();x.moveTo(x0,y);x.quadraticCurveTo(32,y-3+(y-32)*.2,x1,y+(r()-.5)*4);x.stroke()}x.globalAlpha=1;
    x.beginPath();x.ellipse(28,32,20,6,0,0,7);x.globalAlpha=.8;x.fill()});
  cell(12,()=>{x.translate(32,32);x.rotate(.12);x.fillRect(-14,-19,28,38);x.fillStyle="#8c8070";for(let i=0;i<6;i++)x.fillRect(-10,-13+i*5.4,16+((i*7)%5)*1.4,1.6)});
  cell(13,()=>{x.translate(32,32);const g=x.createRadialGradient(0,0,0,0,0,30);g.addColorStop(0,"rgba(255,255,255,1)");g.addColorStop(.2,"rgba(255,255,255,.35)");g.addColorStop(1,"rgba(255,255,255,0)");x.fillStyle=g;
    for(const r of [0,Math.PI/2]){x.save();x.rotate(r);x.beginPath();x.moveTo(-30,0);x.lineTo(0,-3.2);x.lineTo(30,0);x.lineTo(0,3.2);x.fill();x.restore()}x.beginPath();x.arc(0,0,7,0,7);x.fill()});
  cell(14,()=>{const r=rng(11);x.beginPath();for(let i=0;i<=9;i++){const a=i/9*6.283,rr=10+r()*9;x[i?"lineTo":"moveTo"](32+Math.cos(a)*rr,32+Math.sin(a)*rr*.6)}x.globalAlpha=.85;x.fill()});
  cell(15,()=>{for(let i=0;i<=60;i++){const u=i/60,a=-1.4+u*5.6,w=4.2*(1-u*.7);x.beginPath();x.arc(32+Math.cos(a)*20,32+Math.sin(a)*20,w,0,7);x.fill()}});
  const t=new THREE.CanvasTexture(c);t.generateMipmaps=false;t.minFilter=THREE.LinearFilter;return t}
// 刀光的鬃毛紋：沿筆畫（x）方向變化慢、橫向（y）變化快——飛白的條紋
function bristleTexture(){const W=64,H=128,c=document.createElement("canvas");c.width=W;c.height=H;const x=c.getContext("2d"),r=rng(23);x.fillStyle="#000";x.fillRect(0,0,W,H);
  for(let y=0;y<H;y++){const v=r()<.22?r()*.45:.55+.45*r();x.fillStyle=`rgb(${v*255|0},${v*255|0},${v*255|0})`;x.fillRect(0,y,W,1)}
  x.fillStyle="#000";for(let i=0;i<70;i++)x.fillRect(r()*W,r()*H|0,4+r()*24,1+(r()*2|0));
  const t=new THREE.CanvasTexture(c);t.wrapS=THREE.RepeatWrapping;t.wrapT=THREE.ClampToEdgeWrapping;return t}
// 墨潑：不規則墨團＋四散的墨點與拖痕
function splatTexture(){const S=128,c=cv(S),x=c.getContext("2d"),r=rng(7);x.fillStyle="#fff";x.strokeStyle="#fff";x.lineCap="round";
  x.beginPath();for(let i=0;i<=48;i++){const a=i/48*6.283,rr=30*(1+.2*Math.sin(a*3+1)+.14*Math.sin(a*7+2)+.12*(r()-.5));x[i?"lineTo":"moveTo"](64+Math.cos(a)*rr,64+Math.sin(a)*rr)}x.fill();
  for(let i=0;i<20;i++){const a=r()*6.283,d=34+r()*26,rad=1.2+r()*4.5;if(r()<.5){x.lineWidth=rad*.9;x.beginPath();x.moveTo(64+Math.cos(a)*24,64+Math.sin(a)*24);x.lineTo(64+Math.cos(a)*d,64+Math.sin(a)*d);x.stroke()}x.beginPath();x.arc(64+Math.cos(a)*d,64+Math.sin(a)*d,rad,0,7);x.fill()}
  x.globalCompositeOperation="destination-out";for(let i=0;i<26;i++){const a=r()*6.283,d=8+r()*20;x.globalAlpha=.25+r()*.4;x.beginPath();x.arc(64+Math.cos(a)*d,64+Math.sin(a)*d,1+r()*3,0,7);x.fill()}
  return new THREE.CanvasTexture(c)}
// 圓相（一筆畫成的圓，起筆粗、收筆細、尾端飛白）：從正上方順時針畫（揭示著色器依角度逐筆顯示）
function ensoTexture(){const S=256,c=cv(S),x=c.getContext("2d"),r=rng(13),R=100;x.fillStyle="#fff";x.strokeStyle="#000";
  for(let i=0;i<=700;i++){const u=i/700,a=-Math.PI/2+u*Math.PI*2*.94,w=11*(u<.05?.55+u*9:1.05-.78*u)+.8,rr=R+Math.sin(u*9)*2.2;x.beginPath();x.arc(128+Math.cos(a)*rr,128+Math.sin(a)*rr,w,0,7);x.fill()}
  x.globalCompositeOperation="destination-out";x.lineCap="round";for(let k=0;k<16;k++){const off=(r()-.5)*18,a0=-Math.PI/2+(.3+r()*.6)*Math.PI*2,len=.15+r()*.5;x.lineWidth=.8+r()*1.8;x.beginPath();x.arc(128,128,R+off,a0,a0+len);x.stroke()}
  return new THREE.CanvasTexture(c)}
// 印章符紋圈（必殺預警、終焉之言）：外圈粗圓相、內圈虛線、之間 12 組原創符字筆畫、中心一個原創印紋
function sealTexture(){const S=256,c=cv(S),x=c.getContext("2d"),r=rng(29);x.fillStyle="#fff";x.strokeStyle="#fff";x.lineCap="round";
  for(let i=0;i<=600;i++){const u=i/600,a=-Math.PI/2+u*Math.PI*2*.97,w=7*(u<.04?.6+u*10:1-.5*u)+.8;x.beginPath();x.arc(128+Math.cos(a)*116,128+Math.sin(a)*116,w,0,7);x.fill()}
  x.lineWidth=2.6;for(let i=0;i<36;i++){const a=-Math.PI/2+i/36*Math.PI*2;x.beginPath();x.arc(128,128,76,a,a+.11);x.stroke()}
  for(let g=0;g<12;g++){const a=-Math.PI/2+(g+.5)/12*Math.PI*2,cx=128+Math.cos(a)*95,cy=128+Math.sin(a)*95;x.save();x.translate(cx,cy);x.rotate(a+Math.PI/2);
    const n=2+Math.floor(r()*2);for(let k=0;k<n;k++){const t=r();if(t<.4)stroke(x,[[-8,-6+k*6],[8,-5+k*6]],2.8,1.2,10);else if(t<.75)stroke(x,[[-3+k*5,-9],[-2+k*5,9]],3,1,10);else stroke(x,[[6,-8],[0,0],[-8,8]],2.8,1,10)}x.restore()}
  stroke(x,[[100,104],[156,100]],7,3);stroke(x,[[128,82],[126,176]],7.5,2.5);stroke(x,[[150,118],[138,140],[104,160]],6,2);x.beginPath();x.arc(152,156,6,0,7);x.fill();
  return new THREE.CanvasTexture(c)}
// 金色裂紋（弱點擊破）：從中心分岔放射
function crackTexture(){const S=128,c=cv(S),x=c.getContext("2d"),r=rng(31);x.strokeStyle="#fff";x.lineCap="round";
  const br=(px,py,a,len,w,d)=>{if(d>4||len<4)return;const nx=px+Math.cos(a)*len,ny=py+Math.sin(a)*len;x.lineWidth=w;x.beginPath();x.moveTo(px,py);const mx=(px+nx)/2+(r()-.5)*len*.3,my=(py+ny)/2+(r()-.5)*len*.3;x.quadraticCurveTo(mx,my,nx,ny);x.stroke();
    br(nx,ny,a+(r()-.5)*.8,len*.72,w*.7,d+1);if(r()<.6)br(nx,ny,a+(r()<.5?-1:1)*(.5+r()*.6),len*.55,w*.6,d+1)};
  for(let i=0;i<7;i++)br(64,64,i/7*6.283+r()*.5,20+r()*8,3.2,0);
  const g=x.createRadialGradient(64,64,0,64,64,14);g.addColorStop(0,"rgba(255,255,255,.9)");g.addColorStop(1,"rgba(255,255,255,0)");x.fillStyle=g;x.fillRect(0,0,S,S);return new THREE.CanvasTexture(c)}
// 書頁（詞語風暴的旋轉書頁）：泛黃紙、字行、燒紅的邊
function pageTexture(){const c=document.createElement("canvas");c.width=48;c.height=64;const x=c.getContext("2d");x.fillStyle="#d9caa4";x.fillRect(2,2,44,60);x.fillStyle="#6a5a44";for(let i=0;i<8;i++)x.fillRect(8,9+i*6.2,26+((i*5)%9),1.6);
  x.strokeStyle="rgba(255,90,40,.95)";x.lineWidth=3;x.strokeRect(2.5,2.5,43,59);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t}
// 全畫面墨邊（終焉之言的墨色收縮）：四周墨、中間透明，邊緣是筆刷狀的
function veilURL(){const S=256,c=cv(S),x=c.getContext("2d"),r=rng(41);x.fillStyle="#07060a";x.fillRect(0,0,S,S);x.globalCompositeOperation="destination-out";x.filter="blur(7px)";x.fillStyle="#000";
  x.beginPath();for(let i=0;i<=64;i++){const a=i/64*6.283,rr=(.36+.05*Math.sin(a*5+1)+.03*Math.sin(a*13)+.03*r())*S;x[i?"lineTo":"moveTo"](128+Math.cos(a)*rr*1.1,128+Math.sin(a)*rr)}x.fill();return c.toDataURL()}

// 筆刷刀光的著色器：幾何（一條 48 段的帶子）在頂點著色器裡彎成弧線或拉直；片段著色器算「頭粗尾細」的寬度、飛白、收筆後的墨散
const BR_VS=`uniform float uSpan,uW,uStraight,uBend;varying vec2 vUv;
void main(){vUv=uv;vec3 p;
 if(uStraight>.5){float t=uv.x*2.-1.;p=vec3(t,(uv.y-.5)*uW*2.+uBend*(1.-t*t),0.);}
 else{float a=(uv.x-.5)*uSpan;float r=mix(1.-uW,1.,uv.y);p=vec3(cos(a)*r,sin(a)*r,0.);}
 gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);}`;
const BR_FS=`uniform sampler2D uMap;uniform vec3 uColor,uCore;uniform float uProg,uLen,uErode,uOp,uHdr,uInk,uSeed;varying vec2 vUv;
void main(){float s=(vUv.x-(uProg-uLen))/uLen;if(s<0.||s>1.||vUv.x>uProg)discard;
 float y=abs(vUv.y-.5)*2.;
 float th=pow(s,.55);if(s>.88)th*=sqrt(max(0.,1.-pow((s-.88)/.12,2.)));
 float br=texture2D(uMap,vec2(vUv.x*1.7+uSeed,vUv.y)).r;
 float a=smoothstep(0.,.08,th-y-(br-.5)*.14);
 a*=smoothstep(.12,.55,br+pow(s,1.3)*.6);
 a*=smoothstep(uErode,uErode+.22,br*.55+s*.45+.02);
 if(a<.01)discard;
 if(uInk>.5){gl_FragColor=vec4(uColor,a*uOp);return;}
 float core=smoothstep(.6,0.,y/max(th,.02))*smoothstep(.25,.95,s);
 gl_FragColor=vec4(mix(uColor,uCore,core*.8)*uHdr*(.6+.55*br),a*uOp);}`;
// 依角度揭示的圓（圓相、符紋圈）：從正上方順時針逐筆出現
const RV_VS=`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
const RV_FS=`uniform sampler2D uMap;uniform vec3 uColor;uniform float uProg,uOp,uHdr,uInk;varying vec2 vUv;
void main(){vec2 p=vUv-.5;float t=fract((1.5708-atan(p.y,p.x))/6.28318);float a=texture2D(uMap,vUv).a*smoothstep(uProg+.001,uProg-.025,t);if(a<.01)discard;
 gl_FragColor=uInk>.5?vec4(uColor,a*uOp):vec4(uColor*uHdr,a*uOp);}`;

export function createFx(eng,{soul=false}={}){
  const {scene,camera}=eng;
  eng._soulFx=soul;
  const add=makePool(eng,soul?700:500,true,soul?500:500),norm=makePool(eng,400,false,soul?300:400),stk=makeStreaks(eng,soul?260:180,soul?160:180);
  const atlasTex=eng.track(atlasTexture());add.mat.uniforms.uAtlas.value=atlasTex;norm.mat.uniforms.uAtlas.value=atlasTex;
  const setScale=()=>{const s=eng.height*eng.dpr*.5/Math.tan(camera.fov*Math.PI/360);add.mat.uniforms.uScale.value=s;norm.mat.uniforms.uScale.value=s};
  eng.onResize.push(setScale);
  eng.onUpdate(dt=>{add.update(dt);norm.update(dt);stk.update(dt)},50);
  const glowTex=eng.track(glowTexture()),blobTex=eng.track(blobTexture()),circTex=eng.track(circleTexture()),beamTex=eng.track(beamTexture());
  const G={
    arc:new THREE.RingGeometry(.72,1,28,1,0,Math.PI*.95),
    ring:new THREE.RingGeometry(.86,1,40),
    ringThin:new THREE.RingGeometry(.972,1,56),
    plane:new THREE.PlaneGeometry(1,1),
    cyl:new THREE.CylinderGeometry(1,1,1,16,1,true),
    capsule:new THREE.CapsuleGeometry(.5,1,3,8),
    box:new THREE.BoxGeometry(1,1,1),
    cone:new THREE.ConeGeometry(.5,1,6),
  };
  // 尖端收窄的斬痕：把圓弧兩端的寬度縮成 0
  {const p=G.arc.attributes.position,n=p.count;for(let i=0;i<n;i++){const x=p.getX(i),y=p.getY(i),a=Math.atan2(y,x)/(Math.PI*.95),r=Math.hypot(x,y),w=Math.sin(Math.PI*Math.min(1,Math.max(0,a))),rr=lerp(1,r,Math.pow(w,.7));p.setXY(i,x/r*rr,y/r*rr)}}
  for(const k in G)eng.track(G[k]);
  const basic=(color,o={})=>new THREE.MeshBasicMaterial({color,transparent:true,depthWrite:false,blending:o.normal?THREE.NormalBlending:THREE.AdditiveBlending,side:THREE.DoubleSide,fog:false,...(o.map?{map:o.map}:{})});
  // 暫時性的網格：加進場景、播 update(k)、結束後移除並釋放材質
  function temp(mesh,dur,update,ez=ease.lin){scene.add(mesh);mesh.renderOrder=12;update(0,0); // 先套用第 0 格，否則會以全不透明的樣子閃一格
    return eng.tween(dur,(k,r)=>update(k,r),ez).then(()=>{scene.remove(mesh);mesh.traverse(o=>{if(o.material)o.material.dispose()})})}

  /* ---------- DOM 浮字 ---------- */
  // HUD 血條框的位置快取 0.4 秒（每個浮字都量一次會強制重排，連段時很傷）
  let boxCache=null,boxAt=-1e9;
  function hudBoxes(){const now=performance.now();if(boxCache&&now-boxAt<400)return boxCache;boxAt=now;const host=eng.container.parentElement,hb=host?host.getBoundingClientRect():null;
    return boxCache=host?[...host.querySelectorAll(".hpbox")].map(b=>{const r=b.getBoundingClientRect();return{l:r.left-hb.left-6,r:r.right-hb.left+6,t:r.top-hb.top-6,b:r.bottom-hb.top+6,top:r.top-hb.top<hb.height/2}}):[]}
  // cls：dmg（傷害數字）、ono（擬聲字）、good、bad、gold、soul…（樣式在 style.css 的 .v3-t）
  function text(pos,str,cls="",o={}){if(eng.dead)return Promise.resolve();const el=document.createElement("div");el.className="v3-t "+cls;el.textContent=str;el.style.opacity=0;eng.overlay.appendChild(el);
    const p=V(pos).clone(),dx=o.dx==null?rand(-14,14):o.dx,dy=o.dy||0,rise=o.rise==null?46:o.rise,dur=o.dur||.95,rot=o.rot==null?rand(-8,8):o.rot;
    // HUD 血條框的位置（相對戰場），字不要被它蓋住，也不要超出戰場被切掉
    const boxes=hudBoxes();
    const hw=el.offsetWidth/2+4,hh=el.offsetHeight/2+2;
    const place=(x,y)=>{x=Math.max(hw,Math.min(eng.width-hw,x));y=Math.max(hh,Math.min(eng.height-hh,y));
      for(const b of boxes){if(x+hw>b.l&&x-hw<b.r&&y+hh>b.t&&y-hh<b.b){if(b.top)y=b.b+hh;else y=b.t-hh}}return[x,Math.max(hh,Math.min(eng.height-hh,y))]};
    return eng.tween(dur,(k,r)=>{const s=eng.project(p);
      // 彈出（過衝）→ 停留 → 上飄淡出；bounce＝落地彈跳的傷害數字
      const sc=r<.22?ease.back(r/.22):1,up=o.bounce?-Math.abs(Math.sin(r*Math.PI*2.2))*20*(1-r)-rise*r*.5:-rise*ease.out(r),op=r>.7?1-(r-.7)/.3:1;
      // anchor：'l'＝字的左緣對齊該點（往右長）、'r'＝右緣對齊（往左長），讓數字與擬聲字不互疊
      const [x,y]=place(s.x+dx+(o.anchor==="l"?hw:o.anchor==="r"?-hw:0),s.y+dy+up);
      el.style.opacity=op;el.style.transform=`translate(-50%,-50%) translate(${x.toFixed(1)}px,${y.toFixed(1)}px) scale(${(sc*(o.scale||1)).toFixed(3)}) rotate(${rot}deg)`},ease.lin).then(()=>el.remove())}
  // 橫幅：招式名、階段名（用真實時間，不受慢動作影響）
  function banner(str,cls="",dur=1.1){if(eng.dead)return Promise.resolve();const el=document.createElement("div");el.className="v3-banner "+cls;el.innerHTML="<span></span>";el.firstChild.textContent=str;el.style.opacity=0;eng.overlay.appendChild(el);
    return eng.tween(dur,(k,r)=>{const a=r<.18?ease.out(r/.18):r>.8?1-(r-.8)/.2:1;el.style.opacity=a;el.style.transform=`translateX(${((1-Math.min(1,r/.18))*-40+(r>.8?(r-.8)*200:0)).toFixed(1)}px)`},ease.lin,{real:true}).then(()=>el.remove())}
  // 全畫面暈影（紅：危險／受傷，藍：慢動作，白：閃光，暗：天色轉暗），由程式直接設不透明度
  const vig={};for(const k of ["red","blue","white","dark","danger"]){const el=document.createElement("div");el.className="v3-vig "+k;eng.overlay.appendChild(el);vig[k]=el}
  const setVig=(k,a)=>{vig[k].style.opacity=a};
  // 魂系：全畫面閃光安全上限（design.md §5.4：白閃 ≤ 0.15、紅閃 ≤ 0.3）
  const VCAP={white:.15,red:.3,danger:.75};
  const pulseVig=(k,a,dur=.4)=>{if(eng.rm&&k==="white")return Promise.resolve();if(soul&&VCAP[k]!=null)a=Math.min(a,VCAP[k]);return eng.tween(dur,(kk,r)=>setVig(k,a*(1-r)),ease.lin,{real:true})};

  /* ---------- 網格特效 ---------- */
  // 斬痕：面向鏡頭的月牙，沿弧線掃過並淡出。ang＝月牙的傾斜角（弧度）
  function slash(pos,o={}){if(soul)return slashBrush(pos,o);return slashArc(pos,o)}
  function slashArc(pos,{color=0xffffff,size=1,ang=0,dur=.28,sweep=1.3,flip=false}={}){const m=new THREE.Mesh(G.arc,basic(color));m.position.copy(V(pos));const sg=flip?-1:1;
    return temp(m,dur,(k,r)=>{m.quaternion.copy(camera.quaternion);m.rotateZ(ang+sg*sweep*(ease.out3(r)-.5)-Math.PI*.475);m.scale.setScalar(size*(.75+.45*ease.out(r)));m.material.opacity=(soul?.55:1)*(r<.15?r/.15:1-ease.in((r-.15)/.85))})}
  // 地面衝擊環（魂系預設用細線）
  function ring(pos,{color=0xffffff,r0=.2,r1=2,dur=.45,y=.03,opacity=.9,normal=false,thin=soul}={}){const m=new THREE.Mesh(thin?G.ringThin:G.ring,basic(color,{normal}));const p=V(pos);m.position.set(p.x,y,p.z);m.rotation.x=-Math.PI/2;
    return temp(m,dur,(k,r)=>{m.scale.setScalar(lerp(r0,r1,ease.out3(r)));m.material.opacity=opacity*(1-r)})}
  // 面向鏡頭的衝擊環（彈反、命中）
  function burstRing(pos,{color=0xffffff,r0=.1,r1=1.2,dur=.3,thin=soul}={}){const m=new THREE.Mesh(thin?G.ringThin:G.ring,basic(color));m.position.copy(V(pos));
    return temp(m,dur,(k,r)=>{m.quaternion.copy(camera.quaternion);m.scale.setScalar(lerp(r0,r1,ease.out3(r)));m.material.opacity=1-r})}
  const spriteMat=(color,opacity=1)=>new THREE.SpriteMaterial({map:glowTex,color,opacity,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false});
  // 閃光（Sprite）
  // 魂系：閃光依離鏡頭的距離限制大小（畫面高度的 ≤ 22%，手機直式鏡頭很近，否則一個光暈就蓋滿畫面）、亮度與時間也收斂
  let flashLog=[];
  function flash(pos,{color=0xffffff,size=1.5,dur=.25,opacity=1}={}){
    if(soul){const d=camera.position.distanceTo(V(pos)),vh=2*d*Math.tan(camera.fov*Math.PI/360),cap=vh*(eng.aspect<1?.16:.22)/1.5;size=Math.min(size,cap);opacity=Math.min(opacity,.45);dur=Math.min(dur,.18);
      // 同一點 0.12 秒內的閃光（命中、連斬、完美、終結常常同一格各打一個）疊起來經 bloom 會變成蓋住主角的一團光：後到的只留 30%
      const now=eng.time,q=V(pos);flashLog=flashLog.filter(f=>now-f.t<.12);if(flashLog.some(f=>f.p.distanceTo(q)<.8))opacity*=.3;flashLog.push({p:q.clone(),t:now})}
    const m=new THREE.Sprite(spriteMat(color));m.position.copy(V(pos));
    return temp(m,dur,(k,r)=>{m.scale.setScalar(size*(.5+1*ease.out(r)));m.material.opacity=opacity*(1-r)})}
  // 持續發光的光球（火球、蓄力），回傳 {sprite, remove()}
  function orb(pos,{color=0xffaa44,size=.6,opacity=1}={}){const m=new THREE.Sprite(spriteMat(color,opacity));m.position.copy(V(pos));m.scale.setScalar(size);m.renderOrder=12;scene.add(m);
    return{sprite:m,remove(){scene.remove(m);m.material.dispose()}}}
  // 光柱：加色混合＋上下漸層的圓柱，外加一道細亮芯；魂系更細長
  function pillar(pos,{color=0xfff2b0,r=.6,h=9,dur=.5}={}){const p=V(pos),g=new THREE.Group(),rr=soul?r*.3:r;
    const outer=new THREE.Mesh(G.cyl,basic(color,{map:beamTex})),core=new THREE.Mesh(G.cyl,basic(0xffffff,{map:beamTex}));g.add(outer,core);g.position.set(p.x,h/2,p.z);
    return temp(g,dur,(k,r2)=>{const w=rr*(r2<.15?r2/.15:1-ease.in((r2-.15)/.85));outer.scale.set(Math.max(.001,w),h,Math.max(.001,w));core.scale.set(Math.max(.001,w*.3),h,Math.max(.001,w*.3));outer.material.opacity=(soul?.55:.7)*(1-r2*.6);core.material.opacity=.8*(1-r2)})}
  // 閃電：鋸齒狀的帶狀網格（面向鏡頭）
  function bolt(a,b,{color=0xcfe8ff,width=.14,dur=.22,jag=.45,seg=9}={}){const A=V(a),B=V(b),pts=[];const side=new THREE.Vector3().subVectors(B,A).cross(camera.getWorldDirection(new THREE.Vector3())).normalize();
    for(let i=0;i<=seg;i++){const t=i/seg,p=new THREE.Vector3().lerpVectors(A,B,t);if(i&&i<seg)p.addScaledVector(side,rand(-jag,jag)).add(new THREE.Vector3(rand(-jag,jag)*.3,0,rand(-jag,jag)*.3));pts.push(p)}
    const pos=new Float32Array((seg+1)*6),idx=[];pts.forEach((p,i)=>{const w=width*(i===seg?.3:1);pos.set([p.x-side.x*w,p.y-side.y*w,p.z-side.z*w,p.x+side.x*w,p.y+side.y*w,p.z+side.z*w],i*6);if(i<seg){const k=i*2;idx.push(k,k+1,k+2,k+1,k+3,k+2)}});
    const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3));g.setIndex(idx);const m=new THREE.Mesh(g,basic(color));m.frustumCulled=false;
    return temp(m,dur,(k,r)=>{m.material.opacity=r<.5?1:(Math.random()<.5?1:.3)*(1-r)*2}).then(()=>g.dispose())}
  // 魔法陣（貼在地上旋轉），回傳 {mesh, setRadius, setColor, remove()}
  function circle(pos,{color=0x66d9ff,r=1.1,spin=1.2}={}){const m=new THREE.Mesh(G.plane,basic(color,{map:circTex}));const p=V(pos);m.position.set(p.x,.04,p.z);m.rotation.x=-Math.PI/2;m.scale.setScalar(.01);m.renderOrder=9;scene.add(m);
    let alive=true,target=r*2,sc=.01;const off=eng.onUpdate(dt=>{m.rotation.z+=spin*dt;sc=lerp(sc,target,Math.min(1,dt*9));m.scale.setScalar(sc)});
    return{mesh:m,setRadius(v){target=v*2},setColor(c){m.material.color.set(c)},remove(){if(!alive)return;alive=false;eng.tween(.25,k=>{m.material.opacity=1-k}).then(()=>{off();scene.remove(m);m.material.dispose()})}}}
  // 殘影：膠囊剪影
  function ghost(pos,{h=1.7,color=0x9fc4ff,dur=.4,lean=0,rotY=0,opacity=.5}={}){if(soul)return Promise.resolve(); // 魂系不用膠囊殘影
    const m=new THREE.Mesh(G.capsule,basic(color));const p=V(pos);m.position.set(p.x,p.y+h*.5,p.z);m.rotation.set(lean,rotY,0,"YXZ");m.scale.set(h*.3,h*.5,h*.24);
    return temp(m,dur,(k,r)=>{m.material.opacity=opacity*(1-r)})}
  // 假陰影圓片
  function blob(r=.6,opacity=1){const m=new THREE.Mesh(G.plane,new THREE.MeshBasicMaterial({map:blobTex,transparent:true,depthWrite:false,opacity,color:0x000000}));m.rotation.x=-Math.PI/2;m.position.y=.02;m.scale.setScalar(r*2);m.renderOrder=1;return m}

  /* ---------- v2 水墨特效（魂系） ---------- */
  const T2=soul?{bristle:eng.track(bristleTexture()),splat:eng.track(splatTexture()),enso:eng.track(ensoTexture()),seal:eng.track(sealTexture()),crack:eng.track(crackTexture()),page:eng.track(pageTexture())}:{};
  const ribbon=eng.track(new THREE.PlaneGeometry(1,1,48,1));
  const PLAYER_SLASH=0xdfe8ff,GOLD=0xffd27a,INK=0x0b0a0f;
  // 魂系的 slash：玩家刀光（場景傳進來的淡藍白）一律換成金色；白色那層當作白熱芯、不加墨底
  // nextSlash：vfx2 在每一刀之前設定這一刀的粗細／亮度（連斬段數越高越粗）
  const st2={nextSlash:null};
  function slashBrush(pos,{color=0xffffff,size=1,ang=0,dur=.28,sweep=1.3,flip=false}={}){let o={};
    if(color===PLAYER_SLASH){o=st2.nextSlash||{};color=GOLD}
    const white=color===0xffffff;
    return brush(pos,{color,core:0xfff2c0,size:size*.62*(o.size||1),ang,dur:Math.max(.24,dur*(o.dur||1)),sweep,flip,w:(o.w||.26)*(white?.6:1),hdr:(o.hdr||1.2)*(white?.75:1),ink:!white,inkOp:o.inkOp||.62,len:.86})}
  // 筆刷刀光。straight：直線一筆（突刺、斷頭斧、終結橫劃）；len＝可見長度比例；w＝寬度（相對半徑）；ink＝墨色底層（一般混合）
  let liveBrush=0;
  function brush(pos,{color=GOLD,core=0xfff2c0,size=1.2,ang=0,sweep=1.2,flip=false,dur=.3,w=.24,len=.85,hdr=1.15,ink=true,inkColor=INK,inkOp=.62,op=1,straight=false,span=Math.PI*.95,bend=0,stretch=1,toCam=null,draw=.38}={}){
    if(!soul)return slashArc(pos,{color,size,ang,dur,sweep,flip});
    const p=V(pos).clone(),seed=Math.random();
    // 往鏡頭拉近一點，刀光不會被角色身體吃掉一半
    const cam=camera.getWorldPosition(new THREE.Vector3()),dc=cam.clone().sub(p),dl=dc.length();if(dl>.01)p.addScaledVector(dc,Math.min(toCam==null?Math.min(.6,size*.22):toCam,dl*.4)/dl);
    // 可讀性：近景時刀光不能蓋滿畫面——弧形半徑 ≤ 畫面高 24%（直式）／32%（橫式），直線總長 ≤ 畫面寬 70%；
    // 同時存在的加色刀光超過 3 道時，新的一道變淡（連斬＋追加連斬時十幾道疊在一起會經 bloom 洗成一片）；亮度上限 1.25（白熱芯經 bloom 會再放大）。
    {const d=cam.distanceTo(p),vh=2*d*Math.tan(camera.fov*Math.PI/360),vw=vh*eng.aspect;
      if(straight){const L=size*stretch,cap=vw*.7;if(L>cap)stretch*=cap/L}else size=Math.min(size,vh*(eng.aspect<1?.24:.32));
      hdr=Math.min(hdr,1.25);if(liveBrush>=3)op*=Math.max(.35,1-.2*(liveBrush-2))}
    liveBrush++;
    const mk=(c,inkL)=>new THREE.ShaderMaterial({vertexShader:BR_VS,fragmentShader:BR_FS,transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:inkL?THREE.NormalBlending:THREE.AdditiveBlending,
      uniforms:{uMap:{value:T2.bristle},uColor:{value:new THREE.Color(c)},uCore:{value:new THREE.Color(core)},uProg:{value:0},uLen:{value:len},uErode:{value:0},uOp:{value:inkL?inkOp:op},uHdr:{value:hdr*.72},uInk:{value:inkL?1:0},uSeed:{value:seed},
        uSpan:{value:span},uW:{value:inkL?Math.min(.6,w*1.35):w},uStraight:{value:straight?1:0},uBend:{value:bend}}});
    const g=new THREE.Group();g.position.copy(p);const layers=[];
    if(ink){const mi=new THREE.Mesh(ribbon,mk(inkColor,true));mi.renderOrder=11;mi.frustumCulled=false;g.add(mi);layers.push([mi,1])}
    const mc=new THREE.Mesh(ribbon,mk(color,false));mc.renderOrder=12;mc.frustumCulled=false;g.add(mc);layers.push([mc,0]);
    const sg=flip?-1:1;
    return temp(g,dur,(k,r)=>{g.quaternion.copy(camera.quaternion);g.rotateZ(ang+(straight?0:sg*sweep*(ease.out3(Math.min(1,r/draw))-.5)));
      const sc=size*(straight?1:(.85+.25*ease.out(r)));g.scale.set(sc*(straight?stretch:1),sc*sg,sc);
      const pr=ease.out3(Math.min(1,r/draw));
      for(const [m,inkL] of layers){const u=m.material.uniforms;u.uProg.value=inkL?pr*.985:pr;const e0=inkL?.55:.42;u.uErode.value=r<e0?0:ease.in((r-e0)/(1-e0))*1.05}},ease.lin).finally(()=>{liveBrush--})}
  // 圓相：面向鏡頭（預設）或貼地（ground），一筆畫出後擴散淡出
  function enso(pos,{color=GOLD,r0=.3,r1=1.4,dur=.4,ground=false,ink=false,hdr=1.6,op=1,draw=.35,y=.04,spin=0}={}){if(!soul)return burstRing(pos,{color,r0,r1,dur});
    const m=new THREE.Mesh(G.plane,new THREE.ShaderMaterial({vertexShader:RV_VS,fragmentShader:RV_FS,transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:ink?THREE.NormalBlending:THREE.AdditiveBlending,
      uniforms:{uMap:{value:T2.enso},uColor:{value:new THREE.Color(color)},uProg:{value:0},uOp:{value:op},uHdr:{value:hdr*.72},uInk:{value:ink?1:0}}}));const p=V(pos);m.position.copy(p);
    if(!ground){const vh=2*camera.position.distanceTo(p)*Math.tan(camera.fov*Math.PI/360),cap=vh*(eng.aspect<1?.2:.28);if(r1>cap){r0*=cap/r1;r1=cap}}if(ground){m.position.y=y;m.rotation.x=-Math.PI/2}
    const rz=Math.random()*6.28;return temp(m,dur,(k,r)=>{if(!ground){m.quaternion.copy(camera.quaternion);m.rotateZ(rz+spin*r)}else m.rotation.z=rz+spin*r;
      m.scale.setScalar(2*lerp(r0,r1,ease.out3(r)));const u=m.material.uniforms;u.uProg.value=ease.out(Math.min(1,r/draw));u.uOp.value=op*(r<.6?1:1-(r-.6)/.4)},ease.lin)}
  // 地面印章符紋圈：墨色底＋主色加色兩層，T 秒內逐筆畫出；回傳 {group, set(p), remove()}
  function seal(pos,{color=0xff2a1a,r=1.5,T=.8,ink=true,spin=.25,op=1,hdr=1.5,inkOp=.75}={}){const g=new THREE.Group();const p=V(pos);g.position.set(p.x,.035,p.z);g.rotation.x=-Math.PI/2;g.scale.setScalar(r*2);
    const mk=(c,inkL)=>{const m=new THREE.Mesh(G.plane,new THREE.ShaderMaterial({vertexShader:RV_VS,fragmentShader:RV_FS,transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:inkL?THREE.NormalBlending:THREE.AdditiveBlending,
      uniforms:{uMap:{value:T2.seal},uColor:{value:new THREE.Color(c)},uProg:{value:0},uOp:{value:inkL?inkOp:op},uHdr:{value:hdr},uInk:{value:inkL?1:0}}}));m.renderOrder=inkL?8:9;if(inkL){m.scale.setScalar(1.04);m.position.z=-.002}g.add(m);return m};
    const L=[];if(ink)L.push(mk(INK,true));L.push(mk(color,false));scene.add(g);let alive=true,el=0;
    const off=eng.onUpdate(dt=>{el+=dt;const pr=Math.min(1,el/T);for(const m of L)m.material.uniforms.uProg.value=ease.out(pr);g.rotation.z+=spin*dt},60);
    return{group:g,set(q){g.position.x=q.x;g.position.z=q.z},remove(fade=.3){if(!alive)return;alive=false;off();const o0=L.map(m=>m.material.uniforms.uOp.value);
      eng.tween(fade,k=>{L.forEach((m,i)=>m.material.uniforms.uOp.value=o0[i]*(1-k));g.scale.setScalar(r*2*(1+.12*k))}).then(()=>{scene.remove(g);L.forEach(m=>m.material.dispose())})}}}
  // 貼片：墨潑／裂紋等，貼地（ground）或面向鏡頭；normal＝一般混合（墨），否則加色（發光）
  function decal(pos,{tex="splat",color=INK,s0=.3,s1=1.6,dur=1,grow=.25,hold=.35,op=.85,ground=true,normal=true,rot=null,y=.03,aspect=1,keep=false}={}){if(!soul||(!keep&&(eng.fxLow||eng.quality==="low")))return Promise.resolve();
    const m=new THREE.Mesh(G.plane,new THREE.MeshBasicMaterial({map:T2[tex],color,transparent:true,depthWrite:false,side:THREE.DoubleSide,fog:false,toneMapped:normal,blending:normal?THREE.NormalBlending:THREE.AdditiveBlending,polygonOffset:true,polygonOffsetFactor:-2}));
    const p=V(pos);m.position.copy(p);const rz=rot==null?Math.random()*6.28:rot;if(ground){m.position.y=y;m.rotation.set(-Math.PI/2,0,rz)}
    const done=temp(m,dur,(k,r)=>{if(!ground){m.quaternion.copy(camera.quaternion);m.rotateZ(rz)}const g=Math.min(1,r/grow),sc=lerp(s0,s1,ease.out3(g));m.scale.set(sc*aspect,sc,1);m.material.opacity=op*(r<grow+hold?1:1-(r-grow-hold)/Math.max(.01,1-grow-hold))},ease.lin);
    m.renderOrder=ground?8:13;return done}
  // 全畫面墨色收縮：四周的墨往中間壓（k＝壓進來的程度 0–1），停一下再退開淡出。用真實時間（慢動作中也照常）
  let veil=null;
  function inkVeil(k=1,dur=1.1){if(!soul||eng.rm||eng.dead)return Promise.resolve();if(!veil){veil=document.createElement("div");veil.className="v3-vig vx-veil";veil.style.cssText=`background:url(${veilURL()}) center/100% 100% no-repeat;opacity:0;transform-origin:50% 50%`;eng.overlay.appendChild(veil)}
    const el=veil;return eng.tween(dur,(kk,r)=>{const a=r<.3?ease.out(r/.3):r>.65?1-(r-.65)/.35:1,sc=lerp(1.6,1.6-.55*k,r<.3?ease.out3(r/.3):r>.65?1-ease.in((r-.65)/.35)*.5:1);el.style.opacity=(a*.95).toFixed(3);el.style.transform=`scale(${sc.toFixed(3)})`},ease.lin,{real:true}).then(()=>{el.style.opacity=0})}
  // 殘影：把角色目前的姿勢複製一份（骨架凍結、共用幾何），換成單色半透明材質，淡出（＋可漂移、放大）。低畫質不做；同時最多 6 個
  let ghosts=0;
  function afterimage(actor,{color=INK,op=.5,dur=.4,offset=null,additive=false,grow=.04,drift=null,fadeIn=0}={}){if(!soul||!actor||actor.isStandin||!actor.content||!actor.content.parent||eng.quality==="low"||eng.fxLow||ghosts>=6)return null;
    let cl;try{actor.root.updateMatrixWorld(true);cl=skClone(actor.content)}catch(e){return null}
    const mat=new THREE.MeshBasicMaterial({color,transparent:true,opacity:op,depthWrite:false,fog:!additive,blending:additive?THREE.AdditiveBlending:THREE.NormalBlending});
    {const A=[],B=[];actor.content.traverse(o=>A.push(o));cl.traverse(o=>B.push(o));if(A.length===B.length)for(let i=0;i<A.length;i++){const a=A[i],o=B[i];o.visible=a.visible;o.position.copy(a.position);o.quaternion.copy(a.quaternion);o.scale.copy(a.scale)}} // 姿勢與型態部件（P2_*）的顯示照抄當下
    cl.traverse(o=>{if(o.isMesh){o.material=mat;o.castShadow=o.receiveShadow=false;o.frustumCulled=false;if(o.userData.isOutline)o.visible=false}});
    const g=new THREE.Group(),par=new THREE.Matrix4().copy(actor.content.parent.matrixWorld);par.decompose(g.position,g.quaternion,g.scale);if(offset)g.position.add(offset);g.add(cl);const s0=g.scale.clone(),p0=g.position.clone();ghosts++;
    const done=temp(g,dur,(k,r)=>{mat.opacity=op*(fadeIn&&r<fadeIn?r/fadeIn:1-ease.in(fadeIn?(r-fadeIn)/(1-fadeIn):r));g.scale.copy(s0).multiplyScalar(1+grow*r);if(drift)g.position.copy(p0).addScaledVector(drift,r)},ease.lin)
      .then(()=>{ghosts--;cl.traverse(o=>{if(o.isSkinnedMesh&&o.skeleton&&o.skeleton.boneTexture)o.skeleton.dispose()})});
    return{group:g,done}}

  return{emit:o=>add.emit(o),emitN:o=>norm.emit(o),streaks:o=>stk.emit(o),text,banner,setVig,pulseVig,slash,ring,burstRing,flash,orb,pillar,bolt,circle,ghost,blob,temp,basic,G,glowTex,beamTex,setScale,
    brush,enso,seal,decal,inkVeil,afterimage,st2,T2,K,
    get particleCount(){return add.alive+norm.alive},get counts(){return{add:add.alive,norm:norm.alive,streak:stk.alive}}};
}
