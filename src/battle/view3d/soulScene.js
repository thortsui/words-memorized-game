// 魂系模式的 3D 場景：黑暗寫實。
// 無頂的廢墟教堂圓形競技場、濃霧（FogExp2）、閃爍的火盆點光源、從玫瑰窗後方照進來的月光、餘燼粒子。
// 第三人稱鎖定視角：鏡頭在主角右後方、始終對準 Boss，隨雙方移動平滑跟隨；主角依事件自動繞行走位。
import * as THREE from 'three';
import { ease, lerp, rand, clamp } from './engine.js';
import { Actor, createLoader } from './actors.js';
import { standinFor } from './standins.js';
import { createMoves } from './moves.js';

const v3=(x,y,z)=>new THREE.Vector3(x,y,z);
const R0=3.6,TH_MAX=.85,RMAX=6,CAM_RMAX=11; // 主角繞行半徑、繞行角度上限、被擊退的最遠半徑、鏡頭最遠半徑（牆在 12 m）
const BOSS_H={boss_sentinel:3.1,boss_gargoyle:3.0,boss_priest:3.2,boss_executioner:3.4,boss_devourer:3.9};
const EYE={sentinel:0x9dff7a,gargoyle:0xff8a2a,priest:0x8fe9ff,executioner:0xb05cff,devourer:0xff3020};
// 各競技場的色調（同一個場景換霧色、月光與窗光）
const ARENA={
  gate_ruins:{fog:0x18211f,moon:0x9fc4b4,win:0xbfe6cf,dens:.046},
  cathedral_roof:{fog:0x151b28,moon:0x8fb0e8,win:0xa8c8ff,dens:.044},
  frozen_chapel:{fog:0x1b2a37,moon:0xa8dcff,win:0xcdf2ff,dens:.05,snow:true},
  execution_yard:{fog:0x1d1727,moon:0xa890d8,win:0xc9aaff,dens:.05},
  throne_of_words:{fog:0x24130f,moon:0xe2a284,win:0xffba92,dens:.05},
};

/* ---------- 程式產生的貼圖 ---------- */
function floorTexture(){const S=512,c=document.createElement("canvas");c.width=c.height=S;const x=c.getContext("2d"),h=S/2;
  x.fillStyle="#474b52";x.fillRect(0,0,S,S);
  for(let i=0;i<5200;i++){const g=40+Math.random()*60|0;x.fillStyle=`rgba(${g},${g+3},${g+8},.18)`;x.fillRect(Math.random()*S,Math.random()*S,2+Math.random()*3,2+Math.random()*3)}
  x.translate(h,h);const rings=[.16,.34,.52,.7,.86,1],seg=[1,7,11,16,22,28];
  // 每一圈石板：隨機明暗、圈與圈之間的接縫
  for(let r=1;r<rings.length;r++){const r0=rings[r-1]*h,r1=rings[r]*h,n=seg[r],off=Math.random();
    for(let i=0;i<n;i++){const a0=(i+off)/n*Math.PI*2,a1=(i+1+off)/n*Math.PI*2,g=Math.random();x.beginPath();x.arc(0,0,r1,a0,a1);x.arc(0,0,r0,a1,a0,true);x.closePath();
      x.fillStyle=`rgba(${g>.5?255:0},${g>.5?255:0},${g>.5?255:0},${Math.abs(g-.5)*.13})`;x.fill();x.strokeStyle="rgba(12,13,16,.9)";x.lineWidth=2.6;x.stroke()}}
  x.beginPath();x.arc(0,0,rings[0]*h,0,7);x.strokeStyle="rgba(12,13,16,.9)";x.lineWidth=3;x.stroke();
  for(let i=0;i<8;i++){const a=i/8*Math.PI*2;x.beginPath();x.moveTo(0,0);x.lineTo(Math.cos(a)*rings[0]*h,Math.sin(a)*rings[0]*h);x.lineWidth=2;x.stroke()}
  // 青苔與裂縫
  for(let i=0;i<22;i++){const a=Math.random()*7,r=Math.random()*h*.95,px=Math.cos(a)*r,py=Math.sin(a)*r,rr=14+Math.random()*34,g=x.createRadialGradient(px,py,0,px,py,rr);g.addColorStop(0,"rgba(58,74,44,.5)");g.addColorStop(1,"rgba(58,74,44,0)");x.fillStyle=g;x.fillRect(px-rr,py-rr,rr*2,rr*2)}
  x.strokeStyle="rgba(8,8,10,.8)";for(let i=0;i<16;i++){let px=(Math.random()-.5)*S*.9,py=(Math.random()-.5)*S*.9;x.lineWidth=1+Math.random()*1.4;x.beginPath();x.moveTo(px,py);for(let k=0;k<5;k++){px+=(Math.random()-.5)*46;py+=(Math.random()-.5)*46;x.lineTo(px,py)}x.stroke()}
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=4;return t}
function roseTexture(){const S=256,c=document.createElement("canvas");c.width=c.height=S;const x=c.getContext("2d"),h=S/2;x.translate(h,h);
  const g=x.createRadialGradient(0,0,6,0,0,h);g.addColorStop(0,"#ffffff");g.addColorStop(.5,"#dbe8ff");g.addColorStop(1,"#9fb9e6");x.fillStyle=g;x.beginPath();x.arc(0,0,h-4,0,7);x.fill();
  x.strokeStyle="#07080b";x.lineCap="round";x.lineWidth=9;x.beginPath();x.arc(0,0,h-6,0,7);x.stroke();x.lineWidth=6;x.beginPath();x.arc(0,0,h*.62,0,7);x.stroke();x.beginPath();x.arc(0,0,h*.24,0,7);x.stroke();
  for(let i=0;i<12;i++){const a=i/12*Math.PI*2;x.lineWidth=5;x.beginPath();x.moveTo(Math.cos(a)*h*.24,Math.sin(a)*h*.24);x.lineTo(Math.cos(a)*(h-6),Math.sin(a)*(h-6));x.stroke();
    const b=a+Math.PI/12;x.lineWidth=4;x.beginPath();x.arc(Math.cos(b)*h*.8,Math.sin(b)*h*.8,h*.13,0,7);x.stroke();x.beginPath();x.arc(Math.cos(b)*h*.43,Math.sin(b)*h*.43,h*.085,0,7);x.stroke()}
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t}
function mistTexture(){const S=128,c=document.createElement("canvas");c.width=c.height=S;const x=c.getContext("2d");
  for(let i=0;i<16;i++){const px=20+Math.random()*(S-40),py=20+Math.random()*(S-40),r=14+Math.random()*22,g=x.createRadialGradient(px,py,0,px,py,r);g.addColorStop(0,"rgba(255,255,255,.34)");g.addColorStop(1,"rgba(255,255,255,0)");x.fillStyle=g;x.fillRect(0,0,S,S)}
  return new THREE.CanvasTexture(c)}
function shaftTexture(){const c=document.createElement("canvas");c.width=32;c.height=128;const x=c.getContext("2d"),g=x.createLinearGradient(0,0,0,128);g.addColorStop(0,"rgba(255,255,255,.9)");g.addColorStop(1,"rgba(255,255,255,0)");x.fillStyle=g;x.fillRect(0,0,32,128);
  const g2=x.createLinearGradient(0,0,32,0);g2.addColorStop(0,"rgba(0,0,0,1)");g2.addColorStop(.5,"rgba(0,0,0,0)");g2.addColorStop(1,"rgba(0,0,0,1)");x.globalCompositeOperation="destination-out";x.fillStyle=g2;x.fillRect(0,0,32,128);return new THREE.CanvasTexture(c)}

export function createSoulScene(eng,fx,api){
  const {scene,camera,renderer}=eng,load=createLoader();
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.5;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
  const fogC=new THREE.Color(ARENA.gate_ruins.fog);scene.background=fogC;scene.fog=new THREE.FogExp2(fogC,ARENA.gate_ruins.dens);
  // 程式產生的競技場都放在 envProc 裡；arena_cathedral.glb 載入成功後整組隱藏，載入失敗就繼續用它
  const envProc=new THREE.Group();scene.add(envProc);
  const add=(geo,mat,p,s,r)=>{const m=new THREE.Mesh(geo,mat);if(p)m.position.set(p[0],p[1],p[2]);if(s)typeof s==="number"?m.scale.setScalar(s):m.scale.set(s[0],s[1],s[2]);if(r)m.rotation.set(r[0],r[1],r[2]);envProc.add(m);return m};

  /* ---------- 環境反射（很小的一張，讓金屬盔甲有反光） ---------- */
  {const env=new THREE.Scene(),pm=new THREE.PMREMGenerator(renderer);env.background=new THREE.Color(0x0b0e14);
    const sp=new THREE.SphereGeometry(1,8,6),a=new THREE.Mesh(sp,new THREE.MeshBasicMaterial({color:0x9fc0ff})),b=new THREE.Mesh(sp,new THREE.MeshBasicMaterial({color:0xff8a3a})),c=new THREE.Mesh(sp,new THREE.MeshBasicMaterial({color:0x3a4658}));
    a.position.set(-3,6,-8);a.scale.setScalar(3);b.position.set(6,0,6);b.scale.setScalar(2);c.position.set(0,10,0);c.scale.set(8,1,8);env.add(a,b,c);
    const rt=pm.fromScene(env,.04,.1,40);scene.environment=rt.texture;scene.environmentIntensity=.9;eng.track(rt);pm.dispose();sp.dispose();a.material.dispose();b.material.dispose();c.material.dispose()}

  /* ---------- 燈光：月光（唯一投影）、從 Boss 背後打過來的冷色輪廓光、半球環境光 ---------- */
  const hemi=new THREE.HemisphereLight(0x55668a,0x1a1c22,1.6),moon=new THREE.DirectionalLight(ARENA.gate_ruins.moon,3.2);
  moon.position.set(-3.5,13,-11);moon.target.position.set(0,0,1);moon.castShadow=true;moon.shadow.mapSize.set(1024,1024);
  {const c=moon.shadow.camera;c.left=-9;c.right=9;c.top=9;c.bottom=-9;c.near=2;c.far=34;moon.shadow.bias=-.0012;moon.shadow.normalBias=.03}
  const rim=new THREE.DirectionalLight(0x9fb8e8,1.7); // 位置每幀跟著「主角→Boss」方向更新，永遠在 Boss 後上方
  // 蓄力時的紅光：一直存在、平常強度 0（燈的數量不變，就不會重編 shader）
  const danger=new THREE.PointLight(0xff2a1a,0,8,1.8);
  scene.add(hemi,moon,moon.target,rim,rim.target,danger);
  const L0={hemi:hemi.intensity,moon:moon.intensity};

  /* ---------- 程式版競技場（退回方案） ---------- */
  const stone=new THREE.MeshLambertMaterial({color:0x4c5059}),stoneD=new THREE.MeshLambertMaterial({color:0x2e3138}),stoneL=new THREE.MeshLambertMaterial({color:0x5c616b,flatShading:true});
  const box=new THREE.BoxGeometry(1,1,1),cyl=new THREE.CylinderGeometry(1,1,1,10),cone=new THREE.ConeGeometry(1,1,6);
  const floor=add(new THREE.CircleGeometry(9,56),new THREE.MeshStandardMaterial({map:floorTexture(),roughness:.86,metalness:.05}),[0,0,0],1,[-Math.PI/2,0,0]);floor.receiveShadow=true;
  add(new THREE.RingGeometry(9,70,48),new THREE.MeshLambertMaterial({color:0x23262b}),[0,-.01,0],1,[-Math.PI/2,0,0]);
  add(new THREE.TorusGeometry(9.05,.2,5,56),stone,[0,.02,0],[1,1,.6],[Math.PI/2,0,0]);
  // 後牆：兩座高塔、玫瑰窗、尖拱
  const WZ=-13.5;
  add(box,stoneD,[0,3.2,WZ],[9,6.4,1.2]);add(box,stoneD,[-6.3,7.5,WZ],[3.6,15,1.6]);add(box,stoneD,[6.3,7.5,WZ],[3.6,15,1.6]);add(box,stoneD,[0,12.6,WZ],[9,2.6,1.2]);
  add(box,stoneD,[-3.9,8.8,WZ],[1.4,5,1.2]);add(box,stoneD,[3.9,8.8,WZ],[1.4,5,1.2]);
  for(const x of [-6.3,6.3]){add(cone,stoneD,[x,17.2,WZ],[1.5,4.5,1.5]);add(box,stone,[x*.62,5.5,WZ+1],[.7,11,.7])}
  add(cone,stoneD,[0,15.6,WZ],[5.4,3.6,.8]);
  const winMat=new THREE.MeshBasicMaterial({map:roseTexture(),transparent:true,fog:false,color:ARENA.gate_ruins.win});
  add(new THREE.CircleGeometry(2.75,40),winMat,[0,8.9,WZ+.65]);
  const lancet=new THREE.MeshBasicMaterial({color:0x6f8fc0,fog:true});for(const x of [-2.4,-1.2,0,1.2,2.4]){add(box,lancet,[x,3.6,WZ+.62],[.5,2.6,.05]);add(cone,lancet,[x,5.15,WZ+.62],[.29,.6,.03],[0,Math.PI/4,0])}
  // 月光光束
  const shafts=[],shaftTex=shaftTexture();for(let i=0;i<5;i++){const m=new THREE.MeshBasicMaterial({map:shaftTex,transparent:true,opacity:.11,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide,fog:false,color:ARENA.gate_ruins.win});
    const s=add(new THREE.PlaneGeometry(1.6,15),m,[(i-2)*1.15,3.9,WZ+6.4],1,[-1.02,0,(i-2)*.07]);s.renderOrder=8;shafts.push(s)}
  // 側牆與斷柱
  for(const sx of [-1,1])for(let i=0;i<6;i++){const z=-11+i*3.6,h=[10,7.5,11,5,8.5,4][(i+(sx>0?2:0))%6],x=sx*(12.2+(i%2)*.5);
    add(box,i%2?stone:stoneD,[x,h/2,z],[1.7,h,1.7]);if(h>7)add(box,stoneD,[x-sx*.2,h+.3,z+1.8],[1.5,1,3.6]);if(h>9)add(cone,stoneD,[x,h+1.4,z],[1,2.8,1])}
  for(let i=0;i<12;i++){const a=i/12*Math.PI*2+.26,r=10.6,h=[6.5,1.6,5,7.5,2.4,6,.9,7,4.2,6.8,1.2,5.5][i];if(Math.abs(Math.sin(a))<.3&&Math.cos(a)>0)continue;
    const x=Math.sin(a)*r,z=Math.cos(a)*r;add(cyl,stone,[x,h/2,z],[.55,h,.55]);add(box,stoneD,[x,.2,z],[1.5,.4,1.5]);if(h>4)add(box,stoneD,[x,h+.2,z],[1.4,.4,1.4])}
  {const N=90,rub=new THREE.InstancedMesh(new THREE.DodecahedronGeometry(.3,0),stoneL,N),pg=new THREE.InstancedMesh(new THREE.PlaneGeometry(.3,.4),new THREE.MeshLambertMaterial({color:0xb9b29c,side:THREE.DoubleSide}),46),d=new THREE.Object3D();
    for(let i=0;i<N;i++){const a=rand(0,7),r=i<70?rand(8.3,12):rand(5.5,8.2);d.position.set(Math.sin(a)*r,rand(.05,.2),Math.cos(a)*r);d.rotation.set(rand(0,3),rand(0,3),rand(0,3));d.scale.set(rand(.5,1.9),rand(.4,1.2),rand(.5,1.6));d.updateMatrix();rub.setMatrixAt(i,d.matrix)}
    for(let i=0;i<46;i++){const a=rand(0,7),r=rand(2.5,9.5);d.position.set(Math.sin(a)*r,.025+i*.0004,Math.cos(a)*r);d.rotation.set(-Math.PI/2+rand(-.06,.06),0,rand(0,7));d.scale.setScalar(rand(.8,1.3));d.updateMatrix();pg.setMatrixAt(i,d.matrix)}
    envProc.add(rub,pg)}
  // 貼地的霧：兩片幾乎貼著地面的半透明面（太高會在角色身上切出一條水平線）
  const mists=[],mistTex=mistTexture();for(let i=0;i<2;i++){const m=new THREE.MeshBasicMaterial({map:mistTex,transparent:true,opacity:.1,depthWrite:false,color:0x7f8ea6,fog:false});
    const p=new THREE.Mesh(new THREE.PlaneGeometry(24,24),m);p.position.set(rand(-2,2),.06+i*.1,rand(-3,1));p.rotation.set(-Math.PI/2,0,rand(0,6));p.renderOrder=7;p.userData.sp=(i%2?1:-1)*rand(.02,.05);scene.add(p);mists.push(p)}
  // 火盆：鐵籠、炭火（程式版才有）；火焰光球與點光源兩種場景共用，GLB 載入後搬到 FirePoint
  const braziers=[],iron=new THREE.MeshStandardMaterial({color:0x1a1a1d,roughness:.6,metalness:.7}),coal=new THREE.MeshBasicMaterial({color:0xff8a2a}),FIRE=14;
  for(const [a,r] of [[.95,8.1],[-.95,8.1],[2.25,8.3],[-2.25,8.3]]){const x=Math.sin(a)*r,z=Math.cos(a)*r,g=new THREE.Group();g.position.set(x,0,z);envProc.add(g);
    const bowl=new THREE.Mesh(new THREE.CylinderGeometry(.48,.3,.42,8,1,true),iron);bowl.position.y=.95;bowl.material.side=THREE.DoubleSide;g.add(bowl);
    for(let k=0;k<3;k++){const l=new THREE.Mesh(cyl,iron);l.scale.set(.035,.9,.035);const b=k/3*Math.PI*2;l.position.set(Math.sin(b)*.3,.42,Math.cos(b)*.3);l.rotation.set(Math.cos(b)*.2,0,-Math.sin(b)*.2);g.add(l)}
    const c=new THREE.Mesh(new THREE.SphereGeometry(.34,8,6),coal);c.position.y=1.02;c.scale.y=.5;g.add(c);
    const flame=fx.orb(v3(x,1.45,z),{color:0xff7a22,size:1.5,opacity:.9}),light=new THREE.PointLight(0xff7a2a,FIRE,16,1.6);light.position.set(x,1.7,z);scene.add(light);
    braziers.push({pos:v3(x,1.15,z),flame,light,base:FIRE,n:rand(0,9),front:Math.abs(a)<1.5})}

  /* ---------- 場景模型 arena_cathedral.glb ---------- */
  let arenaGLB=null;const winLook=v3(0,5.2,-13);
  // 場中央（主角與 Boss 活動的範圍）的草叢會擋住腳：在 shader 裡把半徑內的草丟掉
  const clearCentre=(m,rad)=>{m.onBeforeCompile=s=>{s.vertexShader=s.vertexShader.replace("#include <common>","#include <common>\nvarying vec2 vWxz;").replace("#include <project_vertex>","#include <project_vertex>\nvWxz=(modelMatrix*vec4(transformed,1.)).xz;");
      s.fragmentShader=s.fragmentShader.replace("#include <common>","#include <common>\nvarying vec2 vWxz;").replace("#include <clipping_planes_fragment>",`#include <clipping_planes_fragment>\nif(length(vWxz)<${rad.toFixed(1)})discard;`)};m.customProgramCacheKey=()=>"clearCentre"+rad;m.needsUpdate=true};
  // 低畫質：拿掉法線與 ORM 貼圖（手機上最吃填色的部分）
  const lowArena=()=>{if(!arenaGLB)return;arenaGLB.traverse(o=>{const m=o.material;if(!m||Array.isArray(m))return;for(const k of ["normalMap","roughnessMap","metalnessMap","aoMap"])if(m[k]){m[k].dispose();m[k]=null}m.needsUpdate=true})};
  // 先讓主角與第一隻 Boss 下載，場景模型（4.4 MB）排在後面，不要三個同時搶頻寬
  const core=Promise.all([load.warm("hero_knight"),load.warm(api.foes[0]&&api.foes[0].model)]);
  const arenaP=core.then(()=>load("arena_cathedral")).then(g=>{if(!g||eng.dead)return;const root=g.scene,fps=[];root.updateMatrixWorld(true);
    root.traverse(o=>{if(o.isMesh){o.receiveShadow=true;o.castShadow=false;if(/Grass/.test(o.name))clearCentre(o.material,7)}if(/^FirePoint/.test(o.name))fps.push(o.getWorldPosition(v3()))});
    envProc.visible=false;scene.add(root);arenaGLB=root;winLook.set(0,10.5,-18);
    // 火焰與點光源搬到模型裡的 FirePoint（離場中央較遠，照射距離放大）
    if(fps.length)braziers.forEach((b,i)=>{const p=fps[i%fps.length];b.pos.set(p.x,p.y+.2,p.z);b.flame.sprite.position.set(p.x,p.y+.45,p.z);b.light.position.set(p.x,p.y+.7,p.z);b.light.distance=24;b.front=p.z>0});
    if(eng.quality==="low")lowArena()});

  const flameC=new THREE.Color(0xff7a2a);let flameK=1,emberT=0,snow=false,snowT=0;
  eng.onUpdate((dt,rdt,t)=>{
    for(const b of braziers){b.n+=dt*9;const f=.82+.12*Math.sin(b.n)+.1*Math.sin(b.n*2.7+1)+rand(-.05,.05);b.light.intensity=b.base*f*flameK;b.light.color.copy(flameC);b.flame.sprite.material.color.copy(flameC);b.flame.sprite.scale.set(1.3*f,1.9*f*(.9+flameK*.1),1)}
    emberT-=dt;if(emberT<=0){emberT=.07;const b=braziers[(Math.random()*braziers.length)|0];
      fx.emit({p:b.pos,n:1,color:[0xff8a2a,0xffc36a,0xff5a1a],speed:[.2,.7],up:rand(.8,1.6),size:[.05,.11],life:[1.4,3],gravity:-.25,drag:.25,radius:.25});
      if(Math.random()<.5)fx.emit({p:v3(rand(-7,7),rand(.2,3),rand(-7,5)),n:1,color:[0xff9a4a,0x8a8f9a],speed:[.05,.3],up:.15,size:[.04,.08],life:[2,4],alpha:.7})}
    if(snow){snowT-=dt;if(snowT<=0){snowT=.05;fx.emitN({p:v3(rand(-8,8),rand(3,6),rand(-8,5)),n:1,color:0xdff3ff,speed:[.1,.4],up:-.9,size:[.05,.1],life:[3,5],alpha:.8})}}
    for(const m of mists)m.rotation.z+=m.userData.sp*dt;
    for(let i=0;i<shafts.length;i++)shafts[i].material.opacity=.09+.035*Math.sin(t*.5+i*1.7)});

  /* ---------- 角色 ---------- */
  // soft：受擊閃光很淡、發光只作用在眼睛與裂縫（見 actors.js）
  const hero=new Actor(eng,fx,{model:"hero_knight",height:1.8,standin:standinFor("hero_knight"),load,castShadow:true,shadow:.5,soft:true});
  let boss=null;
  const H0=v3(0,0,0); // Boss 的原位（場地中心）
  const hs={th:.25,r:R0,roam:false,dir:1,pause:1.5,free:false,walk:false,yaw:Math.PI,tangent:0}; // 主角的極座標走位狀態；tangent≠0 時身體朝移動方向
  function makeBoss(b){const h=BOSS_H[b.model]||3.2;const a=new Actor(eng,fx,{model:b.model,height:h,standin:standinFor(b.model),load,castShadow:true,shadow:h*.3,soft:true});
    a.data=b;a.eye=EYE[b.id]||0xff3020;a.glow(a.eye,0);return a}
  // 模型一次只載入「這一隻」和「下一隻」Boss（每隻約 2–3 MB，不一口氣全抓）
  const preload=i=>{const b=api.foes[i];if(b)load.warm(b.model)};let curIndex=0;
  const bossPos=()=>boss?boss.root.position:H0;
  const heroPolar=()=>{const p=hero.root.position,b=H0;hs.th=Math.atan2(p.x-b.x,p.z-b.z);hs.r=Math.min(RMAX,Math.hypot(p.x-b.x,p.z-b.z))};
  const dust=(p,n=8,c=[0x6b7078,0x8a8f98])=>fx.emitN({p:v3(p.x,.1,p.z),n,color:c,speed:[.4,1.4],flat:.25,up:.4,size:[.3,.6],life:[.4,.9],alpha:.4,drag:2,grow:.8});
  const sparks=(p,n,color=[0xffd9a0,0xffffff,0xff9a3a],sp=7,dir)=>fx.emit({p,n,color,speed:[sp*.25,sp],dir,spread:dir?.7:1,size:[.04,.1],life:[.25,.7],gravity:9,drag:1.2});

  /* ---------- 鎖定視角 ----------
     鏡頭在主角右後方、壓低仰望 Boss。俯仰角與視角每幀自動算：畫面下緣剛好留住主角的腳、上緣留住 Boss 頭頂，
     所以 Boss 會盡量佔滿戰場高度，主角也不會被裁掉。cs 的 fovD／lookUp 是演出用的額外偏移。 */
  const cs={back:3.4,side:1.5,height:1.15,lookK:.8,shift:.1,fovD:0,lookUp:0},CS0={...cs};let cine=null; // cine：過場時直接指定鏡頭 {pos, look, fov}
  const camPos=v3(0,2,8),camLook=v3(0,1.2,0),tp=v3(),tl=v3(),dir=v3(),right=v3();let camInit=false,fovNow=46;
  function camDefaults(){const n=clamp((1.5-eng.aspect)/.7,0,1);CS0.back=3.4-n*.5;CS0.side=1.6-n*.2;CS0.height=1.15-n*.15;CS0.shift=.15+n*.25}
  const csTo=(o,dur=.4,ez=ease.io)=>eng.rm?Promise.resolve():eng.to(cs,o,dur,ez);
  const csReset=(dur=.5)=>eng.to(cs,{...CS0},dur);
  function onResize(){camDefaults();eng.kill(cs);Object.assign(cs,CS0);camera.near=.3;fx.setScale()}
  eng.onResize.push(onResize);
  function updateCamera(rdt){const hp=hero.root.position,bp=bossPos();let wantFov;
    if(cine){tp.copy(cine.pos);tl.copy(cine.look);wantFov=cine.fov||46}
    else{dir.subVectors(bp,hp).setY(0);const d=dir.length()||1;dir.multiplyScalar(1/d);right.set(-dir.z,0,dir.x);
      tp.copy(hp).addScaledVector(dir,-cs.back).addScaledVector(right,cs.side);tp.y=cs.height;
      // 鏡頭不穿出牆外（牆在 12 m）
      const rr=Math.hypot(tp.x,tp.z);if(rr>CAM_RMAX){tp.x*=CAM_RMAX/rr;tp.z*=CAM_RMAX/rr}
      // 用「主角到場中央」的距離來框（Boss 撲過來時畫面不會跟著縮放）
      const d0=Math.max(2,hs.r),bh=(boss?boss.h:3)*1.06,aFeet=-Math.atan2(cs.height+.05,cs.back),aTop=Math.atan2(bh-cs.height,cs.back+d0),mid=(aTop+aFeet)/2,span=(aTop-aFeet)*180/Math.PI+5;
      const hMin=2*Math.atan(Math.tan(21*Math.PI/180)/eng.aspect)*180/Math.PI; // 直式畫面至少要有 42° 的水平視角
      wantFov=clamp(Math.max(span,hMin),34,72)+cs.fovD;
      const ld=cs.back+d*cs.lookK;tl.copy(hp).addScaledVector(dir,d*cs.lookK).addScaledVector(right,-cs.shift);tl.y=cs.height+Math.tan(mid)*ld+cs.lookUp}
    const k=camInit?1-Math.exp(-rdt*(cine?cine.k||3.5:6)):1;camInit=true;camPos.lerp(tp,k);camLook.lerp(tl,k);fovNow=lerp(fovNow,wantFov,k);
    camera.position.copy(camPos);camera.lookAt(camLook);
    if(Math.abs(camera.fov-fovNow)>.02){camera.fov=fovNow;camera.updateProjectionMatrix();fx.setScale()}
    // 輪廓光：永遠從 Boss 後上方照向鏡頭這一側
    dir.subVectors(bp,hp).setY(0).normalize();rim.position.copy(bp).addScaledVector(dir,7);rim.position.y=6.5;rim.target.position.copy(bp);rim.target.position.y=1.5}

  /* ---------- 主角走位：平常慢慢繞著 Boss 走（身體朝行進方向），停下時面向 Boss；Boss 慢慢轉向主角 ---------- */
  const turn=(cur,want,k)=>{let d=want-cur;d=Math.atan2(Math.sin(d),Math.cos(d));return cur+d*k};
  eng.onUpdate((dt,rdt)=>{
    if(!hs.free){
      if(hs.roam&&!eng.rm){hs.pause-=dt;
        if(hs.pause<=0){if(!hs.walk){hs.walk=true;hero.play("Walk");hs.left=rand(2.2,4.5)}
          hs.th+=hs.dir*.11*dt*(R0/Math.max(2,hs.r));hs.left-=dt;if(Math.abs(hs.th)>TH_MAX){hs.th=clamp(hs.th,-TH_MAX,TH_MAX);hs.dir*=-1}
          if(hs.left<=0){hs.walk=false;hero.play("Idle");hs.pause=rand(.8,2);if(Math.random()<.4)hs.dir*=-1}}
        hs.r=lerp(hs.r,R0,Math.min(1,dt*1.2))}
      hero.root.position.set(H0.x+Math.sin(hs.th)*hs.r,hero.root.position.y,H0.z+Math.cos(hs.th)*hs.r)}
    if(boss&&!hs.noFace){const p=hero.root.position,b=boss.root.position,toBoss=Math.atan2(b.x-p.x,b.z-p.z);
      // 行進方向＝圓的切線；走路時身體轉向切線（稍微偏向 Boss），翻滾時完全朝切線
      const sg=hs.tangent||(hs.walk?hs.dir*.8:0),want=sg?toBoss-Math.sign(sg)*Math.min(1,Math.abs(sg))*Math.PI*.5*(hs.tangent?1:.85):toBoss;
      hs.yaw=turn(hs.yaw,want,Math.min(1,dt*(hs.tangent?16:5)));hero.root.rotation.y=hs.yaw}
    if(boss&&!boss.lockYaw){const p=hero.root.position,b=boss.root.position;boss.root.rotation.y=turn(boss.root.rotation.y,Math.atan2(p.x-b.x,p.z-b.z),Math.min(1,dt*3.2))}
    updateCamera(rdt)});
  const stopRoam=()=>{hs.roam=false;if(hs.walk){hs.walk=false;hero.setLoop("Idle");hero.play("Idle")}};

  // 衝到 Boss 面前／後撤回外圈
  async function approach(dur=.28){stopRoam();heroPolar();const r1=(boss?boss.h*.3:.8)+1.1,r0=hs.r;hero.play("Run");dust(hero.root.position,5);
    await eng.tween(dur,k=>{hs.r=lerp(r0,r1,k)},ease.in);hero.setLoop("Idle")}
  async function retreat(dur=.42){hs.free=false;heroPolar();const r0=hs.r,y0=hero.root.position.y;hero.setLoop("Idle");hero.play("Idle");
    await eng.tween(dur,k=>{hs.r=lerp(r0,R0,k);hero.root.position.y=lerp(y0,0,Math.min(1,k*2))},ease.out);hero.root.position.y=0;dust(hero.root.position,4)}

  // 命中 Boss：火花、受擊／踉蹌、傷害數字、頓格、震動
  async function impact(p,{power=1,color=0xffffff}={}){const b=boss;if(!b)return p.onImpact&&p.onImpact();const c=b.center(v3(),.5),hp=hero.root.position;
    p.onImpact&&p.onImpact();b.flash(0xffffff,.25);
    if(!p.kill)b.play(power>=2||(p.last&&p.big)?"Stagger":"Hit");
    const away=v3().subVectors(c,hp).setY(.3).normalize();
    sparks(c,Math.round(10+9*power),[0xffd9a0,0xffffff,color],5+power*1.5,away);fx.burstRing(c,{color,r1:.5+.35*power,dur:.25});fx.flash(c,{color,size:.7+.4*power,dur:.18,opacity:.55});
    fx.emit({p:c,n:Math.round(4+4*power),color:[0x3a1512,0x6a2018],speed:[.5,2.5],dir:away,spread:.8,size:[.08,.18],life:[.4,.8],gravity:5,alpha:.9});
    fx.text(v3(c.x,c.y+b.h*.2,c.z),String(p.dmg),"dmg soul"+(power>=2||p.kill?" big":""),{dur:1,rise:40,dx:rand(20,34)});
    eng.hitStop(45+30*power);eng.shake(.03+.035*power,.28);
    if(p.kill)eng.slowmo(.25,650);
    await eng.wait(power>=2?.32:.18)}
  function dim(k,dur=.35){const h0=hemi.intensity,m0=moon.intensity;return eng.tween(dur,t=>{hemi.intensity=lerp(h0,L0.hemi*(1-k*.6),t);moon.intensity=lerp(m0,L0.moon*(1-k*.6),t)})}
  const camHint=name=>{if(name==="melee")csTo({back:CS0.back-.5,lookK:.9},.3);else if(name==="cast")csTo({back:CS0.back+.4},.4);else if(name==="sky")csTo({back:CS0.back+1,lookUp:1.2,fovD:8},.4);else csReset(.5)};
  const pal={slash:0xdfe8ff,fire:0xff6a1a,thunder:0xbfd6ff,ice:0x9fe6ff,holy:0xffe2a0,meteor:0xffa040};
  const moves=createMoves({eng,fx,hero,foe:()=>boss,soul:true,approach,retreat,impact,cam:camHint,dim,pal});
  // meteorEnd 會直接移動主角（躍起、俯衝），期間暫停極座標走位
  const startMove=async p=>{stopRoam();if((p.move||"")==="meteorEnd")hs.free=true;await moves.start(p)};

  /* ---------- 色調 ---------- */
  let arena=ARENA.gate_ruins,phaseTint=0;
  function setArena(a,dur=1.2){arena=a;phaseTint=0;snow=!!a.snow;const f0=fogC.clone(),f1=new THREE.Color(a.fog),m0=moon.color.clone(),m1=new THREE.Color(a.moon),w0=winMat.color.clone(),w1=new THREE.Color(a.win),d0=scene.fog.density,c0=flameC.clone(),c1=new THREE.Color(0xff7a2a),k0=flameK;
    return eng.tween(dur,k=>{fogC.lerpColors(f0,f1,k);scene.fog.color.copy(fogC);moon.color.lerpColors(m0,m1,k);winMat.color.lerpColors(w0,w1,k);for(const s of shafts)s.material.color.copy(winMat.color);scene.fog.density=lerp(d0,a.dens,k);flameC.lerpColors(c0,c1,k);flameK=lerp(k0,1,k)})}

  /* ---------- Boss 攻擊（閃避題的四種結果共用） ---------- */
  let threat=null,bossBack=Promise.resolve(),atkN=0;
  // 兩種攻擊動作輪流用
  const atkName=()=>atkN%2?"Attack2":"Attack";
  // 蓄力結束後到作答前的時機提示：Boss 頭上的環與主角腳下的環一起隨時限縮小（金色＝還在彈反時間內），紅暈影越來越強
  function startThreat(limitMs,perfectMs){stopThreat();if(!boss)return;let e=0;const mk=c=>{const x=new THREE.Mesh(fx.G.ringThin,fx.basic(c));x.renderOrder=13;scene.add(x);return x};
    const m=mk(0xff2a1a),g=mk(0xffd75a),hm=mk(0xff3a2a),hg=mk(0xffd75a);m.rotation.x=g.rotation.x=-Math.PI/2;hm.material.depthTest=hg.material.depthTest=false;
    const off=eng.onUpdate((dt,rdt)=>{e+=rdt*1000;const k=clamp(e/limitMs,0,1),pk=clamp(e/perfectMs,0,1),hp=hero.root.position,gold=pk<1?.95:Math.max(0,.95-(e-perfectMs)/200);
      m.position.set(hp.x,.05,hp.z);m.scale.setScalar(lerp(3,.7,k));m.material.opacity=.4+.5*k;
      g.position.set(hp.x,.06,hp.z);g.scale.setScalar(lerp(1.4,.7,pk));g.material.opacity=gold;
      if(boss){const c=boss.center(v3(),.82),s=boss.h*.15;
        hm.position.copy(c);hm.quaternion.copy(camera.quaternion);hm.scale.setScalar(s*lerp(2.6,.6,k));hm.material.opacity=.55+.45*k;
        hg.position.copy(c);hg.quaternion.copy(camera.quaternion);hg.scale.setScalar(s*lerp(1.3,.6,pk));hg.material.opacity=gold;
        boss.glow(null,.8+.2*Math.sin(e*(.008+.012*k)));danger.intensity=2.2+1.6*k+.8*Math.sin(e*(.008+.012*k))}
      fx.setVig("red",.1+.3*k+(k>.6?.06*Math.sin(e*.02):0))});
    threat={off,ms:[m,g,hm,hg]}}
  function stopThreat(){danger.intensity=0;if(!threat)return;threat.off();for(const x of threat.ms){scene.remove(x);x.material.dispose()}threat=null;fx.setVig("red",0)}
  // Boss 撲向主角並揮擊：撲近在「命中的那一格」之前就完成；在命中的那一刻 resolve，回傳命中點
  async function bossStrike(speed=1){const b=boss;if(!b)return v3();await bossBack;const name=atkName();atkN++;
    const t=b.impactTime(name,speed),hp=hero.root.position.clone(),d=v3().subVectors(H0,hp).setY(0).normalize(),to=hp.clone().addScaledVector(d,b.h*.55+.6),r=b.root.position,from=r.clone();
    b.play(name,{speed});const lunge=Math.max(.06,t-.05);
    await eng.tween(lunge,k=>{r.lerpVectors(from,to,k)},ease.out);await eng.wait(Math.max(0,t-lunge));
    return hero.center(v3(),.6).addScaledVector(d,.5)}
  // 收招回原位（不等它，下一次攻擊前會自動等）
  function bossRecover(delay=.45){const b=boss;if(!b)return;const r=b.root.position;b.glow(b.eye,phaseTint?.7:0);
    bossBack=eng.wait(delay).then(()=>{if(boss!==b)return;const from=r.clone();return eng.tween(.7,k=>{r.lerpVectors(from,H0,k)},ease.io)})}
  // 主角橫向翻滾：約 0.9 秒，身體朝翻滾方向
  async function roll(amount=.62,dur=.9){heroPolar();const sg=hs.th>0?-1:1;hs.dir=sg;const t0=hs.th,t1=clamp(hs.th+sg*amount,-TH_MAX-.3,TH_MAX+.3);
    hs.tangent=sg;hero.play("Roll",{speed:hero.duration("Roll")/dur});let gt=0;
    await eng.tween(dur*.82,(k,raw)=>{hs.th=lerp(t0,t1,k);if(raw>gt){gt+=.25;fx.ghost(hero.root.position,{h:hero.h*.8,dur:.3,rotY:hero.root.rotation.y})}},ease.io);hs.tangent=0;dust(hero.root.position,5);await eng.wait(dur*.18)}
  const pushBack=(d,dur=.3)=>{heroPolar();const r0=hs.r,r1=Math.min(RMAX,r0+d);return eng.tween(dur,k=>{hs.r=lerp(r0,r1,k);if(Math.random()<.4)dust(hero.root.position,1)},ease.out)};

  /* ---------- 事件 ---------- */
  const H={
    // Boss 登場：在場中央播完整段登場動作（原地起身），鏡頭由遠推近、濃霧慢慢散開，結尾震動＋衝擊波
    async bossEnter(p){stopThreat();moves.abort();if(boss){boss.remove();boss=null}
      const b=boss=makeBoss(p.boss);curIndex=p.index||0;b.root.position.copy(H0);b.root.rotation.y=.2;b.lockYaw=true;b.root.visible=false;
      hs.th=.25;hs.r=R0;hs.free=false;hs.tangent=0;stopRoam();hero.root.position.y=0;hero.play("Idle");
      setArena(ARENA[p.boss.arena]||ARENA.gate_ruins,p.index?1.6:.01);
      await Promise.race([b.ready,eng.wait(2.5,{real:true})]);if(boss!==b)return;b.root.visible=true;
      if(eng.rm){b.lockYaw=false;b.play("Idle");await eng.wait(.6);hs.roam=true;return}
      const has=b.has("Enter"),sp=has?(p.index?Math.max(1,b.duration("Enter")/2.6):1):.5,dur=has?b.duration("Enter",sp):1.6,dens=(ARENA[p.boss.arena]||ARENA.gate_ruins).dens;
      const c0=v3(-3.4,2.4,8.4),c1=v3(-2.8,1.6,4.6),l0=v3(0,b.h*.45,0),l1=v3(0,b.h*.62,0);
      cine={pos:c0.clone(),look:l0.clone(),k:4,fov:44};camPos.copy(c0);camLook.copy(l0);
      const play=b.play("Enter",{speed:sp});
      // 霧從很濃散到正常；鏡頭一路推近
      await eng.tween(dur*.86,(k,raw)=>{cine.pos.lerpVectors(c0,c1,k);cine.look.lerpVectors(l0,l1,k);scene.fog.density=lerp(dens*2.6,dens,ease.out(raw));
        if(Math.random()<.25)fx.emit({p:v3(rand(-1.5,1.5),rand(.1,b.h),rand(-1,1)),n:1,color:[0x8a8f9a,b.eye],speed:[.1,.5],up:.4,size:[.04,.09],life:[.8,1.6],alpha:.6})},ease.io);
      // 站定：震動、細環衝擊波、眼睛亮起
      b.glow(b.eye,1);eng.shake(.08,.6);fx.ring(H0,{color:0x8a94a8,r1:7,dur:.9,opacity:.5});dust(H0,14);
      await Promise.race([play,eng.wait(dur*.14+.3)]);b.setLoop("Idle");b.play("Idle");
      eng.to(b,{glowK:0},.8);b.lockYaw=false;cine=null;await eng.wait(.45);hs.roam=true},
    // 玩家回合開始：腳下一圈金線，主角開始繞行找空檔
    async playerTurn(){preload(curIndex+1); /* 進入玩家回合才預載下一隻 */await bossBack;csReset(.5);hs.roam=true;hs.pause=.3;fx.ring(hero.root.position,{color:0xd9c27a,r1:1.5,dur:.5,opacity:.6});await eng.wait(.25)},
    // 答對：劍上聚起藍白光
    async atb(){const c=hero.center(v3(),.65);fx.emit({p:c,n:10,color:[0x7fc8ff,0xffffff],speed:[.3,1.2],up:.8,size:[.04,.1],life:[.3,.6],radius:.4,kind:1});
      fx.text(hero.center(v3(),1.1),"ATB +1","soul blue",{dur:.7,rise:22});await eng.wait(.12)},
    // 答錯：踉蹌一下
    async miss(){hero.play("Hit",{speed:1.6});dust(hero.root.position,4);await eng.wait(.15)},
    async quickSlash(p){await startMove(p)},
    async skill(p){if(p.big)fx.banner(p.name,"soul",1);await startMove(p)},
    async counter(p){await startMove(p)},
    async hit(p){await moves.hit(p)},
    // 攻擊時間結束：後撤一步，鏡頭拉遠
    async windowEnd(){stopRoam();heroPolar();const r0=hs.r;csTo({back:CS0.back+.4},.4);await eng.tween(.3,k=>{hs.r=lerp(r0,Math.max(r0,R0+.3),k)},ease.out)},
    // 敵人回合開始：Boss 眼睛亮起、踏前一步
    async enemyTurn(){const b=boss;if(!b)return;await bossBack;b.glow(b.eye,1);eng.shake(.03,.3);dust(b.root.position,6);fx.ring(b.root.position,{color:b.eye,r1:b.h*1.1,dur:.5,opacity:.5});await eng.wait(.4);b.glow(b.eye,phaseTint?.7:0)},
    // 轉階段：蜷縮後爆發、衝擊波、霧色改變、火盆轉色；結束後只有眼睛與裂縫留著光
    async bossPhase(p){const b=boss;if(!b)return;stopThreat();await bossBack;stopRoam();fx.banner(p.info.name,"soul phase",1.6);
      csTo({back:CS0.back+1,side:CS0.side+.8,shift:CS0.shift+.3},.5);b.glow(b.eye,.5);b.play("PhaseShift");
      const pre=b.impactTime("PhaseShift");
      await eng.tween(pre,()=>{if(Math.random()<.6){const a=rand(0,7),c=b.center();fx.emit({p:v3(c.x+Math.sin(a)*3,rand(.3,2.5),c.z+Math.cos(a)*3),n:1,color:b.eye,speed:[2.5,4],dir:[-Math.sin(a),0,-Math.cos(a)],spread:.1,size:[.06,.12],life:[.5,.8]})}eng.shake(.015,.1)});
      eng.shake(.16,.9);fx.pulseVig("white",.15,.3);fx.ring(H0,{color:b.eye,r1:10,dur:.9});fx.ring(H0,{color:0xffffff,r1:6.5,dur:.6,opacity:.6});fx.pillar(b.root.position,{color:b.eye,r:b.h*.5,h:12,dur:.8});
      fx.emit({p:b.center(),n:50,color:[b.eye,0xff9a4a,0x8a8f9a],speed:[2,9],size:[.06,.14],life:[.5,1.2],drag:1.4});dust(H0,20);pushBack(.7,.4);hero.play("Guard");
      phaseTint=p.phase;const f0=fogC.clone(),f1=new THREE.Color(arena.fog).lerp(new THREE.Color(b.eye),.06*p.phase).multiplyScalar(.6),d0=scene.fog.density,c0=flameC.clone(),c1=new THREE.Color(0xff7a2a).lerp(new THREE.Color(b.eye),.12),k0=flameK;
      eng.tween(1.2,k=>{fogC.lerpColors(f0,f1,k);scene.fog.color.copy(fogC);scene.fog.density=lerp(d0,arena.dens*(1+.22*p.phase),k);flameC.lerpColors(c0,c1,k);flameK=lerp(k0,1+.15*p.phase,k)});
      await eng.wait(Math.max(1,b.has("PhaseShift")?b.duration("PhaseShift")-pre-.3:1));b.glow(b.eye,.7);csReset(.6);await eng.wait(.3)},
    // 蓄力：Boss 擺出蓄力姿勢、眼睛與裂縫轉紅、身邊亮起紅光、紅粒子往身上聚、鏡頭微推；結束後開始倒數提示
    async telegraph(p){const b=boss;if(!b)return;await bossBack;stopRoam();hero.play("Idle");
      b.play("Telegraph",{hold:true});csTo({back:CS0.back-.4,fovD:-3},.6,ease.out);
      fx.text(b.center(v3(),1.1),"！","soul warn",{dur:.8,rise:10,dx:0,rot:0});
      await eng.tween(.75,k=>{b.glow(0xff2a1a,k);fx.setVig("red",.1*k);danger.position.copy(b.center(v3(),.75)).addScaledVector(dir,-b.h*.55);danger.intensity=2.2*k;
        if(Math.random()<.7){const a=rand(0,7),c=b.center(v3(),.6),e=rand(-1,1);fx.emit({p:v3(c.x+Math.sin(a)*2.4,c.y+e*1.5,c.z+Math.cos(a)*2.4),n:1,color:[0xff2a1a,0xff7a4a],speed:[3,4.5],dir:[-Math.sin(a),-e*.5,-Math.cos(a)],spread:.08,size:[.05,.11],life:[.4,.6]})}},ease.out);
      startThreat(p.limitMs,p.perfectMs)},
    // 彈反：刀劍相擊的火花＋一圈細環、頓格、慢動作，Boss 被震退
    async parry(){stopThreat();const b=boss;if(!b)return;csTo({side:CS0.side+.6,shift:CS0.shift+.3,fovD:-2},.2,ease.out);
      const t=b.impactTime(atkName(),1.1),lead=hero.impactTime("Parry");
      eng.wait(Math.max(0,t-lead)).then(()=>hero.play("Parry"));
      const at=await bossStrike(1.1);
      sparks(at,60,[0xfff2c0,0xffffff,0xffc04a],11);fx.burstRing(at,{color:0xfff2c0,r1:1.5,dur:.35});fx.flash(at,{color:0xfff2c0,size:1.3,dur:.2,opacity:.7});fx.pulseVig("white",.2,.25);
      fx.text(v3(at.x,at.y+.7,at.z),"彈反","soul gold big",{dur:1.2,rise:26,dx:0,rot:0});
      eng.shake(.07,.3);eng.hitStop(140);eng.slowmo(.22,750);
      // Boss 被震退、踉蹌
      b.glow(b.eye,phaseTint?.7:0);b.play("Stagger");const r=b.root.position,from=r.clone();bossBack=eng.tween(.6,k=>{r.lerpVectors(from,H0,k)},ease.out);
      await eng.wait(.3);csReset(.4)},
    // 翻滾閃避：主角朝側面翻滾，Boss 劈空砸在地上
    async dodge(){stopThreat();const b=boss;if(!b)return;const spot=hero.root.position.clone();
      const t=b.impactTime(atkName());const rolled=eng.wait(Math.max(0,t-.38)).then(()=>roll(.62,.9));
      await bossStrike();dust(spot,12);fx.ring(spot,{color:0x8a94a8,r1:1.8,dur:.4,opacity:.6});sparks(v3(spot.x,.15,spot.z),10,[0xffc36a,0xffffff],4);eng.shake(.045,.25);
      fx.text(v3(spot.x,1.5,spot.z),"閃避","soul",{dur:.8,rise:22,dx:0});
      bossRecover(.5);await rolled;csReset(.4)},
    // 勉強格擋：火花四濺、主角被推著向後滑；傷害由接下來的 playerHit 表現
    async guard(){stopThreat();const b=boss;if(!b)return;const t=b.impactTime(atkName());
      eng.wait(Math.max(0,t-hero.impactTime("Guard"))).then(()=>hero.play("Guard"));
      const at=await bossStrike();sparks(at,26,[0xff9a3a,0xffd9a0],7);fx.burstRing(at,{color:0xff9a3a,r1:1,dur:.25});fx.text(v3(at.x,at.y+.6,at.z),"格擋","soul",{dur:.8,rise:20,dx:0})},
    // 擦傷：翻滾慢了半拍，被刀鋒帶到
    async graze(){stopThreat();const b=boss;if(!b)return;const t=b.impactTime(atkName());
      eng.wait(Math.max(0,t-.12)).then(()=>roll(.45,.9));
      const at=await bossStrike();fx.slash(at,{color:0xff4a3a,size:1,ang:.7,dur:.22});sparks(at,10,[0xff6a4a,0xffffff],5)},
    // 中招：Boss 的攻擊結結實實打中；傷害由接下來的 playerHit 表現
    async foeHit(p){stopThreat();const b=boss;if(!b)return;if(p.timeout)hero.play("Guard",{speed:1.6});const at=await bossStrike(1.05);fx.slash(at,{color:0xff3a2a,size:1.5,ang:-.5,dur:.26,sweep:1.6})},
    // 玩家受擊：依 kind（hit／guard／graze）輕重不同（主角只會淡淡閃一下，不會整個變紅）
    async playerHit(p){const c=hero.center(v3(),.6),k=p.kind==="hit"?1:p.kind==="guard"?.45:.55;p.onImpact&&p.onImpact();
      hero.flash(0xff5040,.25);fx.pulseVig("red",.3+.45*k,.35+.3*k);eng.shake(.03+.1*k,.25+.2*k);eng.hitStop(30+90*k);
      fx.text(v3(c.x,c.y+.9,c.z),"-"+p.dmg,"dmg soul hurt"+(k>=1?" big":""),{dur:1,rise:34});
      if(p.kind==="hit"){hero.play("Hit");sparks(c,16,[0xff3a2a,0x8a1a12,0xffffff],6);fx.burstRing(c,{color:0xff3a2a,r1:1.2});pushBack(1.2,.35);dust(hero.root.position,8)}
      else if(p.kind==="guard"){pushBack(.9,.35)}
      else{sparks(c,6,[0xff6a4a],4)}
      bossRecover(.45);await eng.wait(.3+.2*k);if(!p.lethal)csReset(.5)},
    // Boss 倒下：慢動作、播完倒下動作，再化成灰燼與餘燼升空
    async faint(p){stopThreat();moves.abort();const b=boss;if(!b)return;await bossBack;stopRoam();b.glow(b.eye,.6);eng.slowmo(.5,350);csTo({back:CS0.back-.4},.5);
      const dsp=b.has("Die")?Math.max(1,b.duration("Die")/1.3):1,dd=b.duration("Die",dsp);b.play("Die",{hold:true,speed:dsp});await eng.wait(dd*.5);const c=b.center(v3(),.25);
      fx.pillar(b.root.position,{color:0xcfd8e8,r:b.h*.4,h:12,dur:1.1});fx.ring(b.root.position,{color:0xcfd8e8,r1:6,dur:.9,opacity:.6});eng.shake(.05,.5);
      await eng.tween(.9,(k,raw)=>{b.setOpacity(1-raw);b.root.position.y=-.3*raw;b.glowK=.6*(1-raw);
        fx.emit({p:v3(c.x,c.y+rand(-.3,b.h*.4),c.z),n:3,color:[0x8a8f9a,0xff9a4a],speed:[.2,1],up:rand(.8,2),size:[.05,.13],life:[.8,1.8],gravity:-.4,drag:.4,radius:b.h*.25})},ease.lin);
      b.remove();if(boss===b)boss=null;phaseTint=0;
      const d0=scene.fog.density,k0=flameK;eng.tween(1,k=>{scene.fog.density=lerp(d0,arena.dens*.8,k);flameK=lerp(k0,1,k)});csReset(.6);await eng.wait(.1)},
    // 回復：暖色光點從腳下升起
    async heal(p){const hp=hero.root.position;fx.emit({p:hp,n:22,color:[0xffe2a0,0xbfffd0,0xffffff],speed:[.1,.5],up:1.6,size:[.05,.12],life:[.7,1.3],radius:.5,radiusY:.05});
      fx.ring(hp,{color:0xffe2a0,r1:1.3,dur:.6,opacity:.6});fx.text(hero.center(v3(),1.12),"+"+p.amount,"soul heal",{dur:.9,rise:26});await eng.wait(.3)},
    // 勝利：霧散、月光變亮，主角對著後窗舉劍
    async win(){stopRoam();const hp=hero.root.position;hs.noFace=true;hero.root.rotation.y=Math.PI;
      cine={pos:v3(hp.x+1.1,1.0,hp.z+3.4),look:winLook.clone().multiplyScalar(.6).setY(winLook.y*.55),k:1.6,fov:50};
      const d0=scene.fog.density,m0=moon.intensity,h0=hemi.intensity;eng.tween(2.2,k=>{scene.fog.density=lerp(d0,.014,k);moon.intensity=lerp(m0,L0.moon*1.6,k);hemi.intensity=lerp(h0,L0.hemi*1.6,k);for(const s of shafts)s.material.opacity=.1+.14*k},ease.out);
      hero.play("Victory",{hold:true});fx.banner("詞語之火重新點燃","soul",3.6);
      await eng.tween(4.2,()=>{if(Math.random()<.5)fx.emit({p:v3(hp.x+rand(-2,2),rand(0,.4),hp.z+rand(-2,2)),n:1,color:[0xffe2a0,0xffffff],speed:[.1,.4],up:1.2,size:[.05,.12],life:[1,2],gravity:-.2})})},
    // 落敗：主角倒下，鏡頭升高俯視，畫面褪色
    async lose(){stopThreat();stopRoam();moves.abort();const hp=hero.root.position;hs.noFace=true;eng.canvas.classList.add("v3-gray");fx.setVig("dark",.55);
      cine={pos:v3(hp.x+.8,4.6,hp.z+2.8),look:v3(hp.x,.3,hp.z),k:1.2,fov:46};eng.slowmo(.5,900);
      await hero.play("Die",{hold:true});fx.emit({p:hero.center(v3(),.2),n:24,color:[0x8a8f9a,0xff9a4a],speed:[.1,.5],up:.8,size:[.05,.12],life:[1,2.2],radius:.5});fx.banner("灰燼會記得你","soul",2.4);await eng.wait(2.6)},
  };

  onResize();hero.root.position.set(Math.sin(hs.th)*hs.r,0,Math.cos(hs.th)*hs.r);
  const NEED=["hero_knight",api.foes[0]&&api.foes[0].model,"arena_cathedral"];
  // ready：主角＋第一隻 Boss 到齊；場景模型若再 3 秒內到就一起等，否則先用程式場景、到了再換
  return{handlers:H,hero,ready:Promise.all([hero.ready,core]).then(()=>Promise.race([arenaP,new Promise(r=>setTimeout(r,3000))])),progress:()=>load.progress(NEED),
    // 掉幀時：關陰影、關環境反射、只留靠近鏡頭的兩盞火盆光，場景模型拿掉法線／ORM 貼圖
    onQuality(){renderer.shadowMap.enabled=false;moon.castShadow=false;scene.environment=null;for(const b of braziers)if(!b.front){b.light.visible=false}lowArena();scene.traverse(o=>{if(o.material&&!Array.isArray(o.material))o.material.needsUpdate=true})},
    // 指令選單的慢動作：藍色暈影
    setSlow(on){fx.setVig("blue",on?1:0)}};
}
