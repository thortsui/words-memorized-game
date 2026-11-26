// 特效：粒子（Points，一次 draw call）、DOM 浮字（傷害數字／擬聲字）、斬痕、衝擊環、閃光、閃電、光柱、魔法陣、殘影。
// 所有特效都用引擎的遊戲時間，setTimeScale 與頓格會一起影響。
import * as THREE from 'three';
import { ease, lerp, rand } from './engine.js';

const V=p=>p&&p.isVector3?p:new THREE.Vector3(p[0],p[1],p[2]);
const pick=c=>Array.isArray(c)?c[(Math.random()*c.length)|0]:c;

/* ---------- 粒子池 ---------- */
const VS=`attribute float size;attribute vec4 pcolor;attribute float kind;varying vec4 vC;varying float vK;uniform float uScale;
void main(){vC=pcolor;vK=kind;vec4 mv=modelViewMatrix*vec4(position,1.);gl_PointSize=size*uScale/max(.1,-mv.z);gl_Position=projectionMatrix*mv;}`;
// kind 0：柔邊圓點　1：四角星芒　2：實心圓（彩帶、花瓣）　3：愛心（回血招式）
const FS=`varying vec4 vC;varying float vK;
void main(){vec2 p=gl_PointCoord-.5;float d=length(p);float a;
 if(vK<.5){a=smoothstep(.5,.08,d);}
 else if(vK<1.5){float s=abs(p.x)*abs(p.y)*90.;a=max(0.,1.-s)*smoothstep(.5,.2,d);a=max(a,smoothstep(.16,.0,d));}
 else if(vK<2.5){a=step(d,.42);}
 else{vec2 q=vec2(p.x*2.7,.08-p.y*2.7);float u=q.x*q.x+q.y*q.y-1.;float f=u*u*u-q.x*q.x*q.y*q.y*q.y;a=1.-smoothstep(-.03,.03,f);}
 if(a<.01)discard;gl_FragColor=vec4(vC.rgb,vC.a*a);}`;

function makePool(eng,max,additive){
  const pos=new Float32Array(max*3),col=new Float32Array(max*4),size=new Float32Array(max),kind=new Float32Array(max);
  const vel=new Float32Array(max*3),life=new Float32Array(max),maxLife=new Float32Array(max),grav=new Float32Array(max),drag=new Float32Array(max),size0=new Float32Array(max),a0=new Float32Array(max),grow=new Float32Array(max);
  const g=new THREE.BufferGeometry();
  g.setAttribute("position",new THREE.BufferAttribute(pos,3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute("pcolor",new THREE.BufferAttribute(col,4).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute("size",new THREE.BufferAttribute(size,1).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute("kind",new THREE.BufferAttribute(kind,1).setUsage(THREE.DynamicDrawUsage));
  const m=new THREE.ShaderMaterial({vertexShader:VS,fragmentShader:FS,uniforms:{uScale:{value:300}},transparent:true,depthWrite:false,blending:additive?THREE.AdditiveBlending:THREE.NormalBlending});
  const pts=new THREE.Points(g,m);pts.frustumCulled=false;pts.renderOrder=additive?11:10;eng.scene.add(pts);
  let cur=0,alive=0,dirty=false;const c=new THREE.Color();
  function emit(o){let n=o.n||1;if(eng.rm)n=Math.ceil(n*.4);else if(eng.quality==="low"){if(o.deco)return;n=Math.ceil(n*.35)} // 低畫質：裝飾用的粒子（花粉、飄雪）不發，其餘約三分之一
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
      a0[k]=o.alpha==null?1:o.alpha;size0[k]=rand(sz[0],sz[1]);size[k]=size0[k];grow[k]=o.grow||0;
      maxLife[k]=life[k]=rand(lf[0],lf[1]);grav[k]=o.gravity||0;drag[k]=o.drag||0;kind[k]=o.kind||0}
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
function makeStreaks(eng,max){
  const pos=new Float32Array(max*12),col=new Float32Array(max*12),idx=new Uint16Array(max*6);
  for(let i=0;i<max;i++){const v=i*4;idx.set([v,v+1,v+2,v+1,v+3,v+2],i*6)}
  const P=new Float32Array(max*3),Vl=new Float32Array(max*3),life=new Float32Array(max),ml=new Float32Array(max),C=new Float32Array(max*3),W=new Float32Array(max),L=new Float32Array(max),Gr=new Float32Array(max),Dr=new Float32Array(max);
  const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(pos,3).setUsage(THREE.DynamicDrawUsage));g.setAttribute("color",new THREE.BufferAttribute(col,3).setUsage(THREE.DynamicDrawUsage));g.setIndex(new THREE.BufferAttribute(idx,1));
  const m=new THREE.MeshBasicMaterial({vertexColors:true,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide,fog:false,toneMapped:false});
  const mesh=new THREE.Mesh(g,m);mesh.frustumCulled=false;mesh.renderOrder=12;eng.scene.add(mesh);
  let cur=0,alive=0;const c=new THREE.Color(),cam=new THREE.Vector3(),h=new THREE.Vector3(),t=new THREE.Vector3(),d=new THREE.Vector3(),sd=new THREE.Vector3();
  // o：{p, n, color, speed:[a,b], dir, spread, up, life:[a,b], gravity, drag, width, len（拖尾秒數）, hdr（亮度倍率）}
  function emit(o){let n=o.n||10;if(eng.rm)n=Math.ceil(n*.4);else if(eng.quality==="low")n=Math.ceil(n*.4);
    const p=V(o.p),sp=o.speed||[4,12],lf=o.life||[.18,.45],dir=o.dir?V(o.dir):null,spread=o.spread==null?1:o.spread,hdr=o.hdr||3;
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
  return{emit,update,mesh}}

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

export function createFx(eng,{soul=false}={}){
  const {scene,camera}=eng;
  const add=makePool(eng,soul?700:500,true),norm=makePool(eng,400,false),stk=makeStreaks(eng,soul?260:180);
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
  const pulseVig=(k,a,dur=.4)=>eng.rm&&k==="white"?Promise.resolve():eng.tween(dur,(kk,r)=>setVig(k,a*(1-r)),ease.lin,{real:true});

  /* ---------- 網格特效 ---------- */
  // 斬痕：面向鏡頭的月牙，沿弧線掃過並淡出。ang＝月牙的傾斜角（弧度）
  function slash(pos,{color=0xffffff,size=1,ang=0,dur=.28,sweep=1.3,flip=false}={}){const m=new THREE.Mesh(G.arc,basic(color));m.position.copy(V(pos));const sg=flip?-1:1;
    return temp(m,dur,(k,r)=>{m.quaternion.copy(camera.quaternion);m.rotateZ(ang+sg*sweep*(ease.out3(r)-.5)-Math.PI*.475);m.scale.setScalar(size*(.75+.45*ease.out(r)));m.material.opacity=(soul?.55:1)*(r<.15?r/.15:1-ease.in((r-.15)/.85))})}
  // 地面衝擊環（魂系預設用細線）
  function ring(pos,{color=0xffffff,r0=.2,r1=2,dur=.45,y=.03,opacity=.9,normal=false,thin=soul}={}){const m=new THREE.Mesh(thin?G.ringThin:G.ring,basic(color,{normal}));const p=V(pos);m.position.set(p.x,y,p.z);m.rotation.x=-Math.PI/2;
    return temp(m,dur,(k,r)=>{m.scale.setScalar(lerp(r0,r1,ease.out3(r)));m.material.opacity=opacity*(1-r)})}
  // 面向鏡頭的衝擊環（彈反、命中）
  function burstRing(pos,{color=0xffffff,r0=.1,r1=1.2,dur=.3,thin=soul}={}){const m=new THREE.Mesh(thin?G.ringThin:G.ring,basic(color));m.position.copy(V(pos));
    return temp(m,dur,(k,r)=>{m.quaternion.copy(camera.quaternion);m.scale.setScalar(lerp(r0,r1,ease.out3(r)));m.material.opacity=1-r})}
  const spriteMat=(color,opacity=1)=>new THREE.SpriteMaterial({map:glowTex,color,opacity,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false});
  // 閃光（Sprite）
  function flash(pos,{color=0xffffff,size=1.5,dur=.25,opacity=1}={}){const m=new THREE.Sprite(spriteMat(color));m.position.copy(V(pos));
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

  return{emit:o=>add.emit(o),emitN:o=>norm.emit(o),streaks:o=>stk.emit(o),text,banner,setVig,pulseVig,slash,ring,burstRing,flash,orb,pillar,bolt,circle,ghost,blob,temp,basic,G,glowTex,beamTex,setScale,
    get particleCount(){return add.alive+norm.alive}};
}
