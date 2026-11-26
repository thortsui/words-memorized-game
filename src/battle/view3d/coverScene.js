// 封面的 3D 場景（單字魂）：水墨遠山層層疊在濃霧裡，孤身的騎士站在斷崖上，遠方霧中站著一尊巨大的魔王剪影，
// 背後一道金色天光、餘燼往上飄。鏡頭極慢地推近。只用來當封面背景，所有互動都在 DOM。
import * as THREE from 'three';
import { createEngine } from './engine.js';
import { createFx } from './fx.js';
import { Actor, createLoader } from './actors.js';
import { standinFor } from './standins.js';

// 一層水墨山：canvas 畫山脊線（多頻正弦），由上往下淡出，疊在不同深度
function inkMountain(seed,peak,col,solid){const W=1024,H=256,c=document.createElement("canvas");c.width=W;c.height=H;const g=c.getContext("2d");
  let s=seed;const r=()=>(s=(s*16807)%2147483647)/2147483647;const ph=[r()*9,r()*9,r()*9,r()*9];
  const y=x=>{const u=x/W;return H*(1-peak*(.55+.3*Math.sin(u*3.1+ph[0])+.12*Math.sin(u*9.7+ph[1])+.07*Math.sin(u*31+ph[2])+.035*Math.sin(u*83+ph[3])))};
  const gr=g.createLinearGradient(0,0,0,H);gr.addColorStop(0,col);gr.addColorStop(.55,col);gr.addColorStop(1,solid?col:"rgba(0,0,0,0)");
  g.fillStyle=gr;g.beginPath();g.moveTo(0,H);for(let x=0;x<=W;x+=4)g.lineTo(x,y(x));g.lineTo(W,H);g.closePath();g.fill();
  // 皴筆：稜線下方幾道淡淡的斜擦痕
  g.globalCompositeOperation="destination-out";g.strokeStyle="rgba(0,0,0,.18)";
  for(let i=0;i<140;i++){const x=r()*W,y0=y(x)+8+r()*60;g.lineWidth=1+r()*2;g.beginPath();g.moveTo(x,y0);g.lineTo(x+(r()-.5)*40,y0+20+r()*50);g.stroke()}
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t}
function glowTexture(){const c=document.createElement("canvas");c.width=c.height=256;const g=c.getContext("2d"),gr=g.createRadialGradient(128,128,0,128,128,128);
  gr.addColorStop(0,"rgba(255,255,255,1)");gr.addColorStop(.25,"rgba(255,255,255,.45)");gr.addColorStop(1,"rgba(255,255,255,0)");g.fillStyle=gr;g.fillRect(0,0,256,256);return new THREE.CanvasTexture(c)}
function rayTexture(){const c=document.createElement("canvas");c.width=64;c.height=256;const g=c.getContext("2d"),gr=g.createLinearGradient(0,0,64,0);
  gr.addColorStop(0,"rgba(255,255,255,0)");gr.addColorStop(.5,"rgba(255,255,255,1)");gr.addColorStop(1,"rgba(255,255,255,0)");g.fillStyle=gr;g.fillRect(0,0,64,256);
  const v=g.createLinearGradient(0,0,0,256);v.addColorStop(0,"rgba(0,0,0,0)");v.addColorStop(.3,"rgba(0,0,0,1)");v.addColorStop(1,"rgba(0,0,0,1)");
  g.globalCompositeOperation="destination-in";g.fillStyle=v;g.fillRect(0,0,64,256);return new THREE.CanvasTexture(c)}

export function createCover(container,{reducedMotion=false}={}){
  const eng=createEngine(container,{reducedMotion}),{scene,camera,renderer}=eng,fx=createFx(eng,{soul:true}),load=createLoader();
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  eng.usePost({bloom:{strength:.75,radius:.7,threshold:.7},grade:{vig:.55,grain:.045,sat:.82,contrast:1.12,shadow:0xd8e2ff,high:0xffe4b0}});
  const fogC=new THREE.Color(0x15120f);scene.background=fogC;scene.fog=new THREE.FogExp2(fogC,.018);

  // 天空：上暗下亮的暖金漸層（天光從魔王背後照過來）
  {const c=document.createElement("canvas");c.width=4;c.height=256;const g=c.getContext("2d"),gr=g.createLinearGradient(0,0,0,256);
    gr.addColorStop(0,"#07070a");gr.addColorStop(.45,"#1d1814");gr.addColorStop(.72,"#5a4128");gr.addColorStop(.86,"#a07440");gr.addColorStop(1,"#2a2119");g.fillStyle=gr;g.fillRect(0,0,4,256);
    const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;
    const sky=new THREE.Mesh(new THREE.PlaneGeometry(400,140),new THREE.MeshBasicMaterial({map:t,fog:false,depthWrite:false}));sky.position.set(0,32,-120);scene.add(sky)}
  const glowTex=glowTexture(),glow=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex,color:0xffc070,blending:THREE.AdditiveBlending,depthWrite:false,fog:false,opacity:.9}));
  glow.position.set(-2,16,-95);glow.scale.set(80,80,1);scene.add(glow);
  // 水墨遠山（遠→近越來越深）
  const hills=[];
  for(const [z,h,pk,col,sd] of [[-110,52,.95,0x4a3e33,11],[-80,40,.8,0x332b25,23],[-58,30,.7,0x231e1b,37],[-40,22,.6,0x17140f,53]]){
    const m=new THREE.Mesh(new THREE.PlaneGeometry(h*5.2,h),new THREE.MeshBasicMaterial({map:inkMountain(sd,pk,"#"+new THREE.Color(col).getHexString(),z>-50),transparent:true,depthWrite:false}));
    m.position.set(0,h*.5-(z>-50?9:6),z);scene.add(m);hills.push(m)}
  // 最近一層山前面再補一片地面色，魔王的腳藏在山後
  // 金色光柱
  const rayTex=rayTexture(),rays=[];
  for(let i=0;i<6;i++){const m=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({map:rayTex,color:0xffcf86,transparent:true,opacity:.08,blending:THREE.AdditiveBlending,depthWrite:false,fog:false,side:THREE.DoubleSide}));
    m.scale.set(4+Math.random()*6,90,1);m.position.set(-14+i*5.5,30,-60);m.rotation.z=-.32+i*.05;scene.add(m);rays.push({m,ph:Math.random()*6})}

  // 斷崖（主角腳下）
  const rock=new THREE.MeshStandardMaterial({color:0x2a2622,roughness:.95,metalness:0,flatShading:true}),cliff=new THREE.Group();scene.add(cliff);
  for(const [x,y,z,s,sy] of [[0,-1.1,0,2.6,1],[2.4,-1.6,.8,2.2,1.2],[-2.6,-1.5,.6,2.4,1.1],[1,-2.8,2.2,3.2,1.4],[-1.5,-3.2,2.8,3.6,1.5],[4.5,-3,-1,2.8,1.4]]){
    const m=new THREE.Mesh(new THREE.DodecahedronGeometry(1,1),rock);m.position.set(x,y,z);m.scale.set(s,s*.55*sy,s);m.rotation.set(Math.random(),Math.random()*6,Math.random()*.3);m.receiveShadow=true;cliff.add(m)}

  // 燈：背光（金）、側面冷色補光、魔王眼睛的紅光
  const hemi=new THREE.HemisphereLight(0x5a6684,0x1a1410,.9),back=new THREE.DirectionalLight(0xffc27a,4.2),fill=new THREE.DirectionalLight(0x8fa6d8,1.1);
  back.position.set(-3,10,-30);back.target.position.set(0,1,0);back.castShadow=true;back.shadow.mapSize.set(1024,1024);
  {const c=back.shadow.camera;c.left=-4;c.right=4;c.top=4;c.bottom=-4;c.near=10;c.far=50;back.shadow.bias=-.001}
  fill.position.set(6,4,8);scene.add(hemi,back,back.target,fill);
  const eyes=new THREE.PointLight(0xff3020,0,30,1.6);eyes.position.set(-3,13,-40);scene.add(eyes);

  // 主角（背對鏡頭、望向遠方）＋遠方霧中的巨大魔王
  const hero=new Actor(eng,fx,{model:"hero_knight",height:1.8,standin:standinFor("hero_knight"),load,castShadow:true,shadow:.5,soft:true});
  hero.root.position.set(.2,0,0);hero.root.rotation.y=Math.PI+.18;
  const boss=new Actor(eng,fx,{model:"boss_devourer",height:19,standin:standinFor("boss_devourer"),load,shadow:.01});
  boss.root.position.set(-3,-7.5,-46);boss.shadow.visible=false;
  let roarT=null;
  const ready=Promise.all([hero.ready,boss.ready]).then(()=>{if(eng.dead)return;hero.play("Idle");boss.play("Idle");
    // 魔王壓暗成霧中的剪影（發光的部分保留）
    boss.content.traverse(o=>{if(!o.isMesh||!o.material)return;for(const m of Array.isArray(o.material)?o.material:[o.material]){if(m.color&&!/Glow/i.test(m.name||""))m.color.multiplyScalar(.45);if(m.roughness!=null)m.roughness=Math.min(1,m.roughness+.2)}});
    if(reducedMotion)return;
    const roar=()=>{if(eng.dead)return;if(boss.has("Roar"))boss.play("Roar").then(()=>{if(!eng.dead)boss.play("Idle")});
      eng.tween(1.6,k=>{eyes.intensity=60*Math.sin(Math.PI*k)});roarT=setTimeout(roar,14000+Math.random()*8000)};
    roarT=setTimeout(roar,5500)});

  // 餘燼：往上飄的金紅色小點
  const N=reducedMotion?60:220,pos=new Float32Array(N*3),vel=new Float32Array(N*3),eg=new THREE.BufferGeometry();
  const reset=(i,init)=>{pos[i*3]=(Math.random()-.5)*24;pos[i*3+1]=init?Math.random()*14-2:-2;pos[i*3+2]=-Math.random()*22+4;vel[i*3]=(Math.random()-.3)*.4;vel[i*3+1]=.3+Math.random()*.8;vel[i*3+2]=(Math.random()-.5)*.2};
  for(let i=0;i<N;i++)reset(i,true);eg.setAttribute("position",new THREE.BufferAttribute(pos,3));
  const embers=new THREE.Points(eg,new THREE.PointsMaterial({map:glowTex,color:0xff9a40,size:.16,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));scene.add(embers);

  // 鏡頭：主角右後下方仰望遠方魔王；極慢推近、微微呼吸
  const look=new THREE.Vector3(-1.2,3.2,-30);camera.fov=40;camera.updateProjectionMatrix();
  // 寬螢幕：左邊留給標題，畫面主體往右偏
  // 直式手機：按鈕在下半部，畫面往上提，讓騎士露在標題與按鈕之間
  const frame=(w,h)=>{const a=w/h;if(a>1.15)camera.setViewOffset(w,h,-w*.2,0,w,h);else if(a<.8)camera.setViewOffset(w,h,-w*.08,h*.2,w,h);else camera.clearViewOffset()};eng.onResize.push(frame);
  eng.onUpdate((dt,rdt,time)=>{const t=reducedMotion?0:time;
    camera.position.set(2.1+Math.sin(t*.07)*.35,1.35+Math.sin(t*.11)*.08,4.6-Math.min(1.2,t*.02));camera.lookAt(look);
    for(const r of rays)r.m.material.opacity=Math.max(0,.07+.04*Math.sin(t*.4+r.ph));
    glow.material.opacity=.85+.1*Math.sin(t*.3);
    hills.forEach((h,i)=>{h.position.x=Math.sin(t*.03+i)*.3*(i+1)});
    if(!reducedMotion){for(let i=0;i<N;i++){pos[i*3]+=(vel[i*3]+Math.sin(t+i)*.15)*dt;pos[i*3+1]+=vel[i*3+1]*dt;pos[i*3+2]+=vel[i*3+2]*dt;if(pos[i*3+1]>14)reset(i,false)}
      eg.attributes.position.needsUpdate=true}},100);
  eng.start();
  return {dispose(){clearTimeout(roarT);eng.dispose()},ready};
}
