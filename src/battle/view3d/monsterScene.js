// 打怪模式（回合制）的 3D 場景：可愛的日式 RPG 風。
// 明亮草原、藍天白雲、卡通漸層打光＋描邊、圓滾滾的彈性動作、命中星星／擬聲字／彈跳的傷害數字。
// 構圖：主角在左側近處（畫面左下）、怪物在右側遠處（畫面右上），對應 HUD 的位置；出招時鏡頭推拉。
import * as THREE from 'three';
import { ease, lerp, rand, clamp } from './engine.js';
import { Actor, createLoader, toonGradient, LUNGE } from './actors.js';
import { standinFor } from './standins.js';
import { createMoves } from './moves.js';

const v3=(x,y,z)=>new THREE.Vector3(x,y,z);
const HERO=v3(-1.45,0,.85),FOE=v3(1.5,0,-.65);
const BASE_H={slime:1.12,bat:.9};

// 共用的雜訊函式（GLSL）
const NOISE=`float mhs(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float mns(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mhs(i),mhs(i+vec2(1,0)),f.x),mix(mhs(i+vec2(0,1)),mhs(i+vec2(1,1)),f.x),f.y);}
float mfbm(vec2 p){float v=0.,a=.5;for(int i=0;i<3;i++){v+=a*mns(p);p*=2.07;a*=.5;}return v;}`;
// 場景模型的地面只有頂點色（顏色很糊、一大片同一個綠）：在 shader 裡依世界座標加上深淺草塊、細碎草紋與泥土顆粒
function groundDetail(m){m.onBeforeCompile=s=>{
  s.vertexShader=s.vertexShader.replace("#include <common>","#include <common>\nvarying vec3 vWp;varying float vNy;").replace("#include <project_vertex>","#include <project_vertex>\nvWp=(modelMatrix*vec4(transformed,1.)).xyz;vNy=normalize(mat3(modelMatrix)*objectNormal).y;");
  s.fragmentShader=s.fragmentShader.replace("#include <common>","#include <common>\nvarying vec3 vWp;varying float vNy;\n"+NOISE).replace("#include <color_fragment>",`#include <color_fragment>
    if(vNy>.55&&vWp.y<4.){float n=mfbm(vWp.xz*.32),n2=mns(vWp.xz*2.3),fl=mhs(floor(vWp.xz*18.));
      float grass=smoothstep(1.05,1.45,diffuseColor.g/(diffuseColor.r+.02)+(n-.5)*.5);
      vec3 gk=vec3(.84+.3*n)*vec3(.97,1.02,.93)*(.94+.1*n2)*(.96+.07*fl);
      vec3 dk=vec3(.9+.18*n2)*(.93+.12*fl);
      float fade=smoothstep(60.,25.,length(vWp.xz));
      diffuseColor.rgb*=mix(vec3(1.),mix(dk,gk,grass),fade);}`)};
  m.customProgramCacheKey=()=>"groundDetail";m.needsUpdate=true}
// 會隨風擺動的草葉（一個 InstancedMesh）：根部深、葉尖亮，法線朝上（和地面同樣受光，不會一根根閃）
function grassField(root,THREE_,count,grad){const T=THREE_;
  // 地面高度與顏色：把朝上的三角形投影到 0.5 公尺的格子上，記最低的高度（樹冠頂也朝上，取最低才是地面）
  const C=.5,X0=-20,Z0=-26,NX=80,NZ=68,H=new Float32Array(NX*NZ).fill(1e9),R=new Float32Array(NX*NZ),G=new Float32Array(NX*NZ),B=new Float32Array(NX*NZ);
  const a=new T.Vector3(),b=new T.Vector3(),c=new T.Vector3(),ca=new T.Color(),cb=new T.Color(),cc=new T.Color(),e1=new T.Vector3(),e2=new T.Vector3();
  root.updateMatrixWorld(true);
  root.traverse(o=>{if(!o.isMesh)return;const g=o.geometry,P=g.attributes.position,Cl=g.attributes.color,I=g.index,mw=o.matrixWorld;if(!P||!Cl)return;
    const n=I?I.count:P.count;for(let t=0;t<n;t+=3){const ia=I?I.getX(t):t,ib=I?I.getX(t+1):t+1,ic=I?I.getX(t+2):t+2;
      a.fromBufferAttribute(P,ia).applyMatrix4(mw);b.fromBufferAttribute(P,ib).applyMatrix4(mw);c.fromBufferAttribute(P,ic).applyMatrix4(mw);
      if(a.y>3&&b.y>3&&c.y>3)continue;e1.subVectors(b,a);e2.subVectors(c,a);const ny=e1.z*e2.x-e1.x*e2.z,len=e1.clone().cross(e2).length();if(!(len>0)||Math.abs(ny)/len<.8)continue;
      const mnx=Math.max(0,Math.ceil((Math.min(a.x,b.x,c.x)-X0)/C-.5)),mxx=Math.min(NX-1,Math.floor((Math.max(a.x,b.x,c.x)-X0)/C-.5)),mnz=Math.max(0,Math.ceil((Math.min(a.z,b.z,c.z)-Z0)/C-.5)),mxz=Math.min(NZ-1,Math.floor((Math.max(a.z,b.z,c.z)-Z0)/C-.5));
      if(mnx>mxx||mnz>mxz)continue;const d=(b.z-c.z)*(a.x-c.x)+(c.x-b.x)*(a.z-c.z);if(Math.abs(d)<1e-9)continue;
      ca.fromBufferAttribute(Cl,ia);cb.fromBufferAttribute(Cl,ib);cc.fromBufferAttribute(Cl,ic);
      for(let gx=mnx;gx<=mxx;gx++)for(let gz=mnz;gz<=mxz;gz++){const px=X0+(gx+.5)*C,pz=Z0+(gz+.5)*C,w1=((b.z-c.z)*(px-c.x)+(c.x-b.x)*(pz-c.z))/d,w2=((c.z-a.z)*(px-c.x)+(a.x-c.x)*(pz-c.z))/d,w3=1-w1-w2;
        if(w1<-1e-4||w2<-1e-4||w3<-1e-4)continue;const y=a.y*w1+b.y*w2+c.y*w3,k=gz*NX+gx;if(y<H[k]){H[k]=y;R[k]=ca.r*w1+cb.r*w2+cc.r*w3;G[k]=ca.g*w1+cb.g*w2+cc.g*w3;B[k]=ca.b*w1+cb.b*w2+cc.b*w3}}}});
  // 草葉：三段、越往上越窄
  const geo=new T.BufferGeometry(),pos=[],col=[],nor=[],idx=[],SEG=3;
  for(let i=0;i<=SEG;i++){const y=i/SEG,w=.5*(1-y)*(1-y*.15),bend=y*y*.25;pos.push(-w*.1,y,bend*.3,w*.1,y,bend*.3);const k=.78+.36*y;col.push(k,k,k,k,k,k);nor.push(0,1,0,0,1,0);if(i<SEG){const j=i*2;idx.push(j,j+1,j+2,j+1,j+3,j+2)}}
  geo.setAttribute("position",new T.Float32BufferAttribute(pos,3));geo.setAttribute("color",new T.Float32BufferAttribute(col,3));geo.setAttribute("normal",new T.Float32BufferAttribute(nor,3));geo.setIndex(idx);
  const mat=new T.MeshToonMaterial({vertexColors:true,side:T.DoubleSide,gradientMap:grad});const uT={value:0};
  mat.onBeforeCompile=s=>{s.uniforms.uTime=uT;s.vertexShader=s.vertexShader.replace("#include <common>","#include <common>\nuniform float uTime;").replace("#include <begin_vertex>",`#include <begin_vertex>
    vec3 ip=(instanceMatrix*vec4(0.,0.,0.,1.)).xyz;float hh=position.y*position.y;
    float wv=sin(uTime*1.7+ip.x*.55+ip.z*.35)*.6+sin(uTime*2.9+ip.x*1.7-ip.z*.9)*.3+sin(uTime*.6+ip.x*.13)*.4;
    transformed.x+=wv*hh*.28;transformed.z+=wv*hh*.1;`)};
  mat.customProgramCacheKey=()=>"grassWind";
  const im=new T.InstancedMesh(geo,mat,count),d=new T.Object3D(),cl=new T.Color();let n=0;
  for(let tries=0;tries<count*6&&n<count;tries++){const x=X0+Math.random()*NX*C,z=Z0+Math.random()*NZ*C,gx=Math.floor((x-X0)/C),gz=Math.floor((z-Z0)/C),k=gz*NX+gx;
    if(H[k]>1e8||H[k]>2.5)continue;if(G[k]/(R[k]+.02)<1.25)continue; // 泥土路上不長草
    const e=(x/4.9)**2+((z-.1)/2.9)**2;if(e<1)continue; // 戰鬥區（主角與怪物站的地方）留空
    const near=Math.min(1,(e-1)/1.2);if(Math.random()>.25+.75*near)continue;
    const tuft=3+Math.floor(Math.random()*3),base=(.1+Math.random()*.14)*(.6+.4*near),tone=.92+Math.random()*.3;
    for(let j=0;j<tuft&&n<count;j++){const a2=Math.random()*Math.PI*2,r2=Math.random()*.07;d.position.set(x+Math.cos(a2)*r2,H[k]-.02,z+Math.sin(a2)*r2);d.rotation.set(Math.cos(a2)*.35,Math.random()*Math.PI*2,Math.sin(a2)*.35);d.scale.set(.8+Math.random()*.5,base*(.7+Math.random()*.5),1);d.updateMatrix();im.setMatrixAt(n,d.matrix);
      cl.setRGB(R[k],G[k],B[k]).multiplyScalar(tone*(.95+Math.random()*.1));cl.g*=1.05;im.setColorAt(n,cl);n++}}
  im.count=n;if(im.instanceColor)im.instanceColor.needsUpdate=true;im.instanceMatrix.needsUpdate=true;im.computeBoundingSphere&&im.computeBoundingSphere();
  return {mesh:im,tick:dt=>{uT.value+=dt}}}

export function createMonsterScene(eng,fx,api){
  const {scene,camera}=eng,grad=eng.track(toonGradient()),load=createLoader();
  const toon=(color,o={})=>new THREE.MeshToonMaterial({color,gradientMap:grad,...o});
  const add=(geo,mat,p,s,r)=>{const m=new THREE.Mesh(geo,mat);if(p)m.position.set(p[0],p[1],p[2]);if(s)typeof s==="number"?m.scale.setScalar(s):m.scale.set(s[0],s[1],s[2]);if(r)m.rotation.set(r[0],r[1],r[2]);env.add(m);return m};
  // 程式產生的草原都放在 env 裡；arena_meadow.glb 載入成功後整組隱藏，載入失敗就繼續用它
  const env=new THREE.Group();scene.add(env);

  /* ---------- 天空、燈光 ---------- */
  {const c=document.createElement("canvas");c.width=4;c.height=256;const x=c.getContext("2d"),g=x.createLinearGradient(0,0,0,256);
    g.addColorStop(0,"#2f86e6");g.addColorStop(.45,"#6db9f5");g.addColorStop(.72,"#c4e8ff");g.addColorStop(1,"#eaf8ff");x.fillStyle=g;x.fillRect(0,0,4,256);
    const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;scene.background=t}
  scene.fog=new THREE.Fog(0xd4eeff,32,95);
  // 後製：微微提高飽和與對比、很淡的暗角；泛光門檻高，只有特效（星星、魔法）會暈開
  eng.usePost({bloom:{strength:.4,radius:.45,threshold:1.05},grade:{vig:.1,grain:0,sat:1.08,contrast:1.04,shadow:0xf0f4ff,high:0xfffaf0}});
  const hemi=new THREE.HemisphereLight(0xdff1ff,0x9bd77a,1.25),sun=new THREE.DirectionalLight(0xfff1d0,1.9);sun.position.set(-4,8,5);scene.add(hemi,sun);
  const L0={hemi:hemi.intensity,sun:sun.intensity};

  /* ---------- 草原 ---------- */
  const sph=new THREE.SphereGeometry(1,16,10),cone=new THREE.ConeGeometry(1,1,7),cyl=new THREE.CylinderGeometry(1,1,1,10),box=new THREE.BoxGeometry(1,1,1),circ=new THREE.CircleGeometry(1,40);
  const grassM=toon(0x86d95c),R=-Math.PI/2;
  add(circ,grassM,[0,0,0],110,[R,0,0]);
  for(const [x,z,s,c] of [[-6,-5,5,0x7bd052],[7,-9,7,0x93e066],[-2,-14,8,0x7bd052],[5,3,4,0x93e066],[-8,4,5,0x8fdf63]])add(circ,toon(c),[x,.01,z],[s,s*.6,1],[R,0,rand(0,3)]);
  // 泥土戰場
  add(circ,toon(0xe0bf86),[0,.02,.1],[4.3,2.5,1],[R,0,.12]);add(circ,toon(0xecd09b),[.1,.03,.1],[3.3,1.8,1],[R,0,.12]);
  // 遠丘、雪山、城堡
  for(const [x,z,s,h,c] of [[-22,-34,16,5,0x7fcf62],[14,-38,20,6,0x74c95c],[38,-46,22,8,0x86d46a],[-46,-50,24,9,0x86d46a],[0,-56,30,7,0x93dc74]])add(sph,toon(c),[x,-.5,z],[s,h,s*.7]);
  for(const [x,z,s,h] of [[-30,-78,16,24],[-14,-84,13,18],[8,-90,18,27],[30,-82,14,19],[-52,-86,15,20]]){add(cone,toon(0x8eaee0,{fog:true}),[x,h/2-1,z],[s,h,s]);add(cone,toon(0xffffff),[x,h-1-h*.16,z],[s*.33,h*.34,s*.33])}
  {const wall=toon(0xf2e6cc),roof=toon(0xe5653d),cx=13.5,cz=-38,cy=5.2;
    add(box,wall,[cx,cy+1.3,cz],[5.5,2.6,3]);add(box,wall,[cx,cy+3.2,cz-.3],[2.2,2.6,2.2]);add(cone,roof,[cx,cy+5.3,cz-.3],[1.9,1.8,1.9]);
    for(const dx of [-3,3]){add(cyl,wall,[cx+dx,cy+1.9,cz+1.2],[.9,3.8,.9]);add(cone,roof,[cx+dx,cy+4.5,cz+1.2],[1.2,1.6,1.2])}
    add(box,toon(0x8a5a3a),[cx,cy+.7,cz+1.52],[1,1.4,.1])}
  // 樹、石牆、路牌
  const trunk=toon(0x9a6a43),leaf=[toon(0x4fb04a),toon(0x62c257)];
  for(const [x,z,s] of [[-7.5,-8,1.5],[-11,-15,1.9],[8.5,-11,1.6],[4.5,-19,1.5],[-4,-22,1.7],[13,-6,1.3]]){add(cyl,trunk,[x,s*.8,z],[s*.2,s*1.6,s*.2]);add(sph,leaf[0],[x,s*2.2,z],[s*1.2,s*1.05,s*1.2]);add(sph,leaf[1],[x-s*.6,s*1.8,z+.3],s*.8);add(sph,leaf[1],[x+s*.65,s*1.9,z+.2],s*.75)}
  const stone=[toon(0xb9bcc4),toon(0xa3a7b2)];for(let i=0;i<9;i++)add(sph,stone[i%2],[3.6+i*.48+rand(-.05,.05),.2+(i%3===0?.12:0),-3.3-i*.22],[.3,.24+rand(0,.08),.26]);
  add(cyl,trunk,[-4.2,.6,-3.2],[.07,1.2,.07]);add(box,toon(0xc48a55),[-4.2,1.05,-3.2],[.7,.22,.06],[0,.4,.05]);
  // 花與草叢（InstancedMesh，各一次 draw call）
  {const N=170,fl=new THREE.InstancedMesh(new THREE.SphereGeometry(.07,6,4),new THREE.MeshBasicMaterial(),N),tu=new THREE.InstancedMesh(new THREE.ConeGeometry(.07,.26,4),toon(0x58b84a),260);
    const d=new THREE.Object3D(),col=new THREE.Color(),pal=[0xffe14d,0xffffff,0xff9ad1,0xc59bff,0xffb347];
    const spot=()=>{for(;;){const a=rand(0,Math.PI*2),r=rand(2.2,17),x=Math.cos(a)*r,z=Math.sin(a)*r-3;if((x/4.6)**2+(z/2.8)**2>1&&z<2.9)return[x,z]}};
    for(let i=0;i<N;i++){const [x,z]=spot();d.position.set(x,.1,z);d.scale.setScalar(rand(.7,1.3));d.rotation.set(0,0,0);d.updateMatrix();fl.setMatrixAt(i,d.matrix);fl.setColorAt(i,col.set(pal[i%pal.length]))}
    for(let i=0;i<260;i++){const [x,z]=spot();d.position.set(x,.12,z);d.scale.set(rand(.8,1.4),rand(.8,1.8),rand(.8,1.4));d.rotation.set(rand(-.2,.2),rand(0,3),rand(-.2,.2));d.updateMatrix();tu.setMatrixAt(i,d.matrix)}
    fl.instanceColor.needsUpdate=true;env.add(fl,tu)}
  // 雲：慢慢往右飄
  const clouds=[];{const cm=new THREE.MeshLambertMaterial({color:0xffffff,emissive:0x9fb6c8,fog:false});
    for(const [x,y,z,s] of [[-26,17,-60,5],[4,21,-70,6.5],[30,15,-58,4.5],[-48,22,-75,6],[52,20,-72,5.5]]){const g=new THREE.Group();g.position.set(x,y,z);
      for(const [dx,dy,k] of [[0,0,1],[-1.1,-.15,.7],[1.2,-.1,.75],[.4,.35,.65]]){const m=new THREE.Mesh(sph,cm);m.position.set(dx*s,dy*s,0);m.scale.set(s*k,s*k*.55,s*k*.6);g.add(m)}env.add(g);clouds.push(g)}}
  eng.onUpdate(dt=>{if(eng.quality==="low")return;for(const c of clouds){c.position.x+=dt*.5;if(c.position.x>70)c.position.x=-70}});
  // 空中飄的花粉／花瓣
  let pollenT=0;eng.onUpdate(dt=>{pollenT-=dt;if(pollenT<=0){pollenT=.35;fx.emitN({p:v3(rand(-5,5),rand(.3,2.6),rand(-4,2.5)),n:1,color:[0xffffff,0xfff3a0,0xffd1e8],speed:[.1,.35],dir:[1,.15,0],spread:.5,size:[.05,.1],life:[2.5,4.5],kind:2,alpha:.8,deco:true})}});

  /* ---------- 場景模型 arena_meadow.glb（頂點色、無貼圖）：轉成卡通材質，載入失敗就維持上面的程式草原 ---------- */
  let arena=null,grass=null;
  // 先讓主角與第一隻怪物下載，場景模型排在後面（不要三個同時搶頻寬）
  const core=Promise.all([load.warm("hero_cute"),load.warm(api.foes[0]&&api.foes[0].model)]);
  const arenaP=core.then(()=>load("arena_meadow")).then(g=>{if(!g||eng.dead)return;const root=g.scene;
    root.traverse(o=>{if(!o.isMesh)return;const old=o.material;o.material=new THREE.MeshToonMaterial({vertexColors:true,gradientMap:grad,side:old.side});groundDetail(o.material);old.dispose();o.frustumCulled=true});
    try{const gf=grassField(root,THREE,eng.dpr>=2?7000:9000,grad);root.add(gf.mesh);grass=gf;eng.onUpdate(dt=>{if(grass&&grass.mesh.visible)grass.tick(dt)})}catch(e){console.warn("[view3d] grass",e)}
    // 程式草原整組移出場景（只設 visible=false 的話，裡面一百多個物件每幀還是會被走訪、重算矩陣）；釋放交給 eng.track
    env.visible=false;scene.remove(env);eng.track({dispose:()=>eng.disposeObject(env)});scene.add(root);arena=root;scene.fog.near=60;scene.fog.far=330;camera.far=400;camera.updateProjectionMatrix();
    if(eng.quality==="low")lowArena()});
  // 低畫質：場景模型壓縮後只剩一個合併的網格（一次 draw call，沒有單獨的花可以藏），這裡只把它的矩陣凍結；
  // 省下來的主要是角色描邊（每個部位少畫一次）、粒子與每幀的矩陣更新，見 onQuality。
  const lowArena=()=>{if(grass)grass.mesh.visible=false;if(arena)arena.traverse(o=>{o.matrixAutoUpdate=false})};

  /* ---------- 鏡頭 ---------- */
  const rig={pos:v3(0,0,0),look:v3(0,0,0),zoom:1},CAM={},rigTok={n:0};let atBase=true;
  function presets(){const a=eng.aspect,narrow=clamp((1.5-a)/.7,0,1); // 直式畫面時把鏡頭拉遠、抬高一點
    CAM.base={pos:v3(-.25,1.6+narrow*.3,6.1+narrow*.4),look:v3(.05,1.0,0),zoom:1};
    CAM.hero={pos:v3(-1.9,1.35,4.5),look:v3(-1.1,.7,.5),zoom:1};
    CAM.foe={pos:v3(.5,1.3,4.3),look:v3(1.2,.75,-.4),zoom:1};
    CAM.melee={pos:v3(.2,1.35,4.9+narrow*.4),look:v3(.75,.7,-.3),zoom:1};
    CAM.cast={pos:v3(-.9,1.5,5.3+narrow*.5),look:v3(-.2,.8,.2),zoom:1};
    CAM.sky={pos:v3(-.3,1.3,7.6+narrow*.6),look:v3(.4,1.3,-.2),zoom:1};
    CAM.wide={pos:v3(0,2.5,7.4+narrow),look:v3(0,.9,0),zoom:1}}
  const fovFor=()=>{const hf=43*Math.PI/180;return clamp(2*Math.atan(Math.tan(hf/2)/eng.aspect)*180/Math.PI,30,64)};
  function cam(name,dur=.45,ez=ease.io){if(eng.rm)name="base";const t=CAM[name]||CAM.base;atBase=name==="base";const tok=++rigTok.n,p0=rig.pos.clone(),l0=rig.look.clone();
    return eng.tween(dur,k=>{if(tok!==rigTok.n)return;rig.pos.lerpVectors(p0,t.pos,k);rig.look.lerpVectors(l0,t.look,k)},ez)}
  function onResize(){presets();camera.fov=fovFor();camera.near=.3;camera.updateProjectionMatrix();fx.setScale();if(atBase){rig.pos.copy(CAM.base.pos);rig.look.copy(CAM.base.look)}}
  eng.onResize.push(onResize);
  eng.onUpdate((dt,rdt,t)=>{camera.position.copy(rig.pos);if(!eng.rm&&eng.quality!=="low"){camera.position.x+=Math.sin(t*.45)*.07;camera.position.y+=Math.sin(t*.6)*.035}camera.lookAt(rig.look)});
  function dim(k,dur=.35){const h0=hemi.intensity,s0=sun.intensity,b0=scene.backgroundIntensity;return eng.tween(dur,t=>{hemi.intensity=lerp(h0,L0.hemi*(1-k*.75),t);sun.intensity=lerp(s0,L0.sun*(1-k*.8),t);scene.backgroundIntensity=lerp(b0,1-k*.72,t)})}

  /* ---------- 角色 ---------- */
  const hero=new Actor(eng,fx,{model:"hero_cute",height:1.22,standin:standinFor("hero_cute"),cute:true,toon:grad,outline:true,load});
  // 面向對手，但稍微朝鏡頭轉一點，才看得到臉
  const faceFoe=()=>{hero.face(FOE);hero.root.rotation.y-=.75};
  hero.root.position.copy(HERO);faceFoe();
  let foe=null;
  function makeFoe(m){const kind=m.model.startsWith("bat")?"bat":"slime",h=BASE_H[kind]*(m.scale||1);
    const a=new Actor(eng,fx,{model:m.model,height:h,standin:standinFor(m.model),cute:true,toon:grad,outline:true,load,fly:kind==="bat"?h*.75:0,keepOrigin:kind==="bat",shadow:h*(kind==="bat"?.34:.5)});
    a.kind=kind;a.data=m;a.root.position.copy(FOE);a.face(HERO);a.root.rotation.y+=.3;return a}
  // 模型一次只載入「這一隻」和「下一隻」，不一口氣全抓（手機流量與記憶體）
  const preload=i=>{const m=api.foes[i];if(m)load.warm(m.model)};
  const dust=(p,n=8)=>fx.emitN({p:v3(p.x,.08,p.z),n,color:[0xf3e3bd,0xffffff],speed:[.5,1.6],flat:.25,up:.5,size:[.2,.42],life:[.3,.6],alpha:.7,drag:2,grow:.6});
  const stars=(p,n,sp=4.5)=>fx.emitN({p,n,color:[0xfff27a,0xffffff,0xffb347,0xff8fc7],speed:[sp*.4,sp],size:[.24,.5],life:[.35,.75],gravity:6,drag:1.6,kind:1});

  // 主角衝到怪物面前（小跳步）／跳回原位
  function meleeSpot(){const d=v3().subVectors(HERO,FOE).setY(0).normalize();return FOE.clone().addScaledVector(d,foe.h*.6+.95)}
  async function approach(dur=.3){const r=hero.root.position,from=r.clone(),to=meleeSpot();hero.play("Run");dust(from,6);
    await eng.tween(dur,k=>{r.lerpVectors(from,to,k);r.y=Math.sin(k*Math.PI)*.22},ease.io);r.y=0;hero.setLoop("Idle");dust(to,5)}
  async function retreat(dur=.34){const r=hero.root.position,from=r.clone();if(from.distanceTo(HERO)<.05){hero.setLoop("Idle");hero.play("Idle");return}
    hero.setLoop("Idle");hero.play("Idle");
    await eng.tween(dur,k=>{r.lerpVectors(from,HERO,k);r.y=lerp(from.y,0,k)+Math.sin(k*Math.PI)*.55},ease.io);r.y=0;faceFoe();dust(HERO,6);
    hero.pose.scale.set(1.18,.8,1.18);eng.to(hero.pose.scale,{x:1,y:1,z:1},.3,ease.elastic)}

  // 命中怪物
  async function impact(p,{power=1,ono,color=0xffffff}={}){const f=foe;if(!f)return p.onImpact&&p.onImpact();const c=f.center();
    p.onImpact&&p.onImpact();f.flash(0xffffff,1);f.play("Hit");
    // 被打退一小步再彈回來
    const r=f.root.position,back=v3().subVectors(FOE,HERO).setY(0).normalize().multiplyScalar(.12+.1*power);
    eng.tween(.34,k=>{const s=Math.sin(k*Math.PI);r.x=FOE.x+back.x*s;r.z=FOE.z+back.z*s},ease.out);
    stars(c,Math.round(7+6*power),3.5+power);fx.burstRing(c,{color:0xffffff,r1:.5+.3*power});fx.flash(c,{color,size:.8+.5*power,dur:.2,opacity:.8});
    fx.text(v3(c.x,c.y+f.h*.45,c.z),"-"+p.dmg,"dmg"+(power>=2||p.kill?" big":""),{bounce:true,dur:1.05,rise:36,dx:rand(10,20),dy:-6,anchor:"l"});
    if(ono)fx.text(v3(c.x,c.y+f.h*.45,c.z),ono,"ono"+(power>=2?" big":""),{dur:.75,rise:26,dx:rand(-20,-10),dy:-30,anchor:"r"});
    eng.hitStop(35+32*power);eng.shake(.025+.03*power,.26);
    if(p.kill){eng.slowmo(.35,380);stars(c,16,7)}
    await eng.wait(power>=2?.3:.17)}

  const pal={slash:0xfff6c2,fire:0xff8a2a,thunder:0xfff06a,ice:0x8fe3ff,holy:0xffe9a0,meteor:0xffb347};
  const moves=createMoves({eng,fx,hero,foe:()=>foe,soul:false,approach,retreat,impact,cam,dim,pal});
  let aura=null; // 連招蓄力的魔法陣
  const clearAura=()=>{if(aura){aura.remove();aura=null}};
  let cure=null; // 回血招式的綠色魔法陣
  const clearCure=()=>{if(cure){cure.remove();cure=null}};

  /* ---------- 事件 ---------- */
  const H={
    // 怪物登場：從天而降、落地擠壓彈跳，鏡頭先看怪物再拉回
    async enter(p){if(foe){foe.remove();foe=null}const f=foe=makeFoe(p.monster);f.root.visible=false;
      await Promise.race([f.ready,eng.wait(2.5,{real:true})]);if(foe!==f)return;
      faceFoe();cam("foe",.4);f.root.visible=true;const r=f.root.position;
      const land=()=>{dust(FOE,14);fx.ring(FOE,{color:0xffffff,r1:f.h*1.6+.6,opacity:.7,normal:true});eng.shake(.03+f.h*.03,.25)};
      if(f.has("Enter")){ // 片段本身就是「從天而降＋落地」，落地大約在 0.33 秒
        r.y=0;if(f.kind!=="bat")eng.wait(.33).then(()=>{if(foe===f)land()});await f.play("Enter")}
      else{r.y=5;f.play("Idle");await eng.tween(.42,k=>{r.y=5*(1-k)},ease.in);land();f.pose.scale.set(1.35,.6,1.35);await eng.to(f.pose.scale,{x:1,y:1,z:1},.5,ease.elastic)}
      if(p.monster.boss){fx.text(f.center(v3(),1.25),"魔王登場！","ono big",{dur:1.1});stars(f.center(),14,5)}
      f.play("Idle");await cam("base",.45);preload((p.index||0)+1)}, // 這一隻登場完才預載下一隻
    // 答對得能量：藍色星光被主角吸收、主角小跳一下
    async gain(p){const c=hero.center();fx.emit({p:c,n:12,color:[0x5ad1ff,0xffffff],speed:[.5,1.6],up:1.2,size:[.1,.2],life:[.4,.8],radius:.5,kind:1});
      if(p.amount)fx.text(hero.center(v3(),1.15),"+"+p.amount,"good",{dur:.8,rise:30});
      const P=hero.pose.position;eng.tween(.28,k=>{P.y=Math.sin(k*Math.PI)*.16},ease.lin);await eng.wait(.16)},
    async hold(){await eng.wait(.05)},
    // 連招蓄力開始：腳下出現魔法陣
    async chainStart(p){clearAura();aura=fx.circle(HERO,{color:0xffd23f,r:.8});cam("hero",.4);hero.play("Cast");
      fx.text(hero.center(v3(),1.25),"蓄力！","gold",{dur:.9});fx.emit({p:HERO,n:18,color:[0xffd23f,0xffffff],speed:[.3,1],up:2,size:[.1,.2],life:[.5,.9],radius:.7,radiusY:.05,kind:1});
      await eng.wait(.5);cam("base",.4)},
    // 每答對一題：魔法陣變大、光柱一閃
    async chainCharge(p){if(!aura)aura=fx.circle(HERO,{color:0xffd23f,r:.8});aura.setRadius(.8+.5*p.stage/p.total);if(p.ready)aura.setColor(0xffffff);
      fx.pillar(HERO,{color:0xffe58a,r:.5+.3*p.stage/p.total,h:5,dur:.4});fx.emit({p:HERO,n:14,color:[0xffd23f,0xffffff],speed:[.3,1],up:2.6,size:[.1,.22],life:[.4,.8],radius:.7,radiusY:.05,kind:1});
      fx.text(hero.center(v3(),1.25),`${p.stage} / ${p.total}`,"gold",{dur:.7,rise:24});
      const s=hero.pose.scale;s.set(1.12,.86,1.12);eng.to(s,{x:1,y:1,z:1},.35,ease.elastic);await eng.wait(.3)},
    // 發動：橫幅＋閃光
    async chainFire(p){fx.banner(p.skill.name,"cute",1.2);fx.pulseVig("white",.6,.3);fx.ring(HERO,{color:0xffd23f,r1:3.5,dur:.5});stars(hero.center(),14,5);hero.play("Victory");cam("wide",.3);await eng.wait(.55)},
    async chainStage(p){fx.text(hero.center(v3(),1.3),`第 ${p.stage} 式`,"gold",{dur:.6,rise:20});await eng.wait(.04)},
    async chainDone(){clearAura();hero.play("Victory");stars(hero.center(v3(),.9),10,3.5);await eng.wait(.45)},
    // 連招中斷：魔法陣碎掉、主角嚇一跳
    async chainBreak(){clearAura();fx.emit({p:hero.center(v3(),.2),n:22,color:[0x9aa0b5,0xd7dbea],speed:[1,3.5],flat:.4,size:[.1,.24],life:[.4,.8],gravity:5});
      fx.text(hero.center(v3(),1.2),"中斷…","bad",{dur:.8});hero.play("Hit");await eng.wait(.35)},
    // 回血招式起手：鏡頭用 cast、主角吟唱，腳下浮出綠色魔法陣、光點往上飄（命中與回復在 heal 事件）
    async skill(p){if(p.heal){clearCure();cam("cast",.4);hero.play("Cast",{hold:true});cure=fx.circle(HERO,{color:0x7dffa0,r:hero.h*.95,spin:.9});
        fx.emit({p:HERO,n:16,color:[0x7dffa0,0xffe58a,0xffffff],speed:[.2,.7],up:1.8,size:[.08,.16],life:[.5,.9],radius:hero.h*.6,radiusY:.05,kind:1});
        await eng.wait(.42);return}
      if(p.big&&!p.chainStage)fx.banner(p.name,"cute",1);await moves.start(p)},
    async hit(p){await moves.hit(p)},
    // 怪物出手：史萊姆跳起來壓過去、蝙蝠俯衝；撞到主角面前才 resolve，接著由 playerHit 表現命中
    async foeAttack(p){const f=foe;if(!f)return;cam("hero",.35);const r=f.root.position,d=v3().subVectors(FOE,HERO).setY(0),dist=d.length();d.normalize();
      fx.text(f.center(v3(),1.2),"！","bad",{dur:.5,rise:14});
      f.play("Attack");const t=f.impactTime("Attack");
      if(f.has("Attack")){ // 真模型的攻擊片段自己會往前衝 LUNGE×身高：只把怪物平移到「衝完剛好貼到主角面前」的位置，不再另外加跳弧
        const stop=f.h*.5+.55+(LUNGE[f.kind]||0)*f.h,to=HERO.clone().addScaledVector(d,stop);
        await eng.tween(Math.max(.05,t),k=>{r.lerpVectors(FOE,to,k)},ease.io)}
      else{const to=HERO.clone().addScaledVector(d,f.h*.45+.45),pre=Math.max(.05,t-.3);await eng.wait(pre);
        const arc=f.kind==="bat"?.25:.9+f.h*.3;await eng.tween(Math.min(.3,t),k=>{r.lerpVectors(FOE,to,k);r.y=Math.sin(k*Math.PI)*arc},ease.in)}},
    // 玩家受擊：主角閃紅、彈開、傷害數字；怪物跳回原位
    async playerHit(p){const c=hero.center();p.onImpact&&p.onImpact();hero.flash(0xff4040,1);hero.play("Hit");
      stars(c,8,3.5);fx.burstRing(c,{color:0xff6a6a,r1:.9});fx.pulseVig("red",.55,.4);fx.text(v3(c.x,c.y+.6,c.z),"-"+p.dmg,"dmg hurt",{bounce:true,dur:1,rise:30,dx:rand(8,16),anchor:"l"});fx.text(v3(c.x,c.y+.6,c.z),"砰！","ono",{dur:.6,rise:20,dx:rand(-16,-8),dy:-28,anchor:"r"});
      eng.hitStop(70);eng.shake(.07,.3);dust(HERO,6);
      const f=foe;if(f){const r=f.root.position,clip=f.has("Attack");
        // 真模型：等攻擊片段自己退回去，再把位置平移回原位（不加跳弧）；替身：跳回去
        if(clip)await eng.wait(.3);else f.play("Idle");const from=r.clone();
        await eng.tween(clip?.45:.36,k=>{r.lerpVectors(from,FOE,k);if(!clip)r.y=Math.sin(k*Math.PI)*.6},ease.io);r.y=0;if(!clip)dust(FOE,5)}else await eng.wait(.3);
      cam("base",.4)},
    // 怪物倒下：扁掉、變成星星消失
    async faint(p){const f=foe;if(!f)return;cam("foe",.35);moves.abort();clearAura();clearCure();
      await f.play("Faint",{hold:true});const c=f.center(v3(),.3);
      stars(c,22,5.5);fx.flash(c,{color:0xffffff,size:f.h*2.4});fx.ring(FOE,{color:0xffffff,r1:f.h*2,opacity:.7});
      fx.emitN({p:c,n:16,color:[0xffffff,0xfff3c0],speed:[.4,1.4],up:1.5,size:[.3,.6],life:[.5,1],alpha:.75,grow:.8});
      await eng.tween(.3,k=>{f.root.scale.setScalar(Math.max(.001,1-k));f.setOpacity(1-k*.5)},ease.in);
      f.remove();if(foe===f)foe=null;hero.play("Victory");await eng.wait(.4);cam("base",.35)},
    // 回復：回血招式＝綠／金色光柱從天而降、愛心往上飄、頭上冒綠色 +N；打倒怪物的回復＝綠色光點上升
    async heal(p){if(p.source==="skill"){const c=hero.center(),h=hero.h;
        fx.pillar(HERO,{color:0x3fd870,r:.5,h:6,dur:.9});fx.flash(c,{color:0x7dffa0,size:h*1.2,dur:.3,opacity:.45});
        p.onImpact&&p.onImpact();hero.flash(0x7dffa0,.85);
        fx.emitN({p:hero.center(v3(),.25),n:12,color:[0xff8fc7,0xff6fa8,0xff9ad1,0x7dffa0],speed:[.15,.5],up:1.6,size:[.18,.3],life:[.9,1.5],radius:h*.55,radiusY:.1,drag:.8,gravity:-.6,kind:3,alpha:.95});
        fx.emit({p:HERO,n:20,color:[0x7dffa0,0xffe58a,0xffffff],speed:[.2,.8],up:2.2,size:[.08,.18],life:[.6,1.1],radius:h*.6,radiusY:.05,kind:1});
        fx.ring(HERO,{color:0x9dffb8,r1:1.5,dur:.55,opacity:.8});
        fx.text(hero.center(v3(),1.25),"+"+p.amount,"cure",{bounce:true,dur:1.15,rise:34});
        const s=hero.pose.scale;s.set(1.14,.86,1.14);eng.to(s,{x:1,y:1,z:1},.4,ease.elastic);
        await eng.wait(.3);hero.play("Victory");await eng.wait(.55);clearCure();await cam("base",.4);return}
      const c=HERO.clone();p.onImpact&&p.onImpact();fx.emit({p:c,n:22,color:[0x7dffa0,0xffffff,0xb8ffcf],speed:[.2,.7],up:2,size:[.1,.22],life:[.6,1.1],radius:.55,radiusY:.05,kind:1});
      fx.ring(HERO,{color:0x7dffa0,r1:1.4,dur:.5});fx.text(hero.center(v3(),1.2),"+"+p.amount+" HP","good",{dur:.9});hero.flash(0x7dffa0,.6);await eng.wait(.45)},
    // 勝利：主角歡呼、彩帶、鏡頭拉近
    async win(){cam("hero",.6);hero.root.rotation.y=Math.atan2(camera.position.x-HERO.x,camera.position.z-HERO.z);
      const conf=()=>fx.emitN({p:v3(HERO.x+rand(-1.5,1.5),3.2,HERO.z+rand(-.5,1)),n:26,color:[0xff5a79,0xffd23f,0x5ad1ff,0x7dffa0,0xc59bff],speed:[.3,1.6],size:[.1,.2],life:[1.2,2.2],gravity:1.6,drag:.8,kind:2});
      conf();fx.banner("勝利！","cute",1.4);await hero.play("Victory");conf();hero.play("Victory");await eng.wait(.5)},
    // 落敗：主角倒下、畫面變灰
    async lose(){cam("hero",.6);moves.abort();clearAura();clearCure();eng.canvas.classList.add("v3-gray");if(foe)foe.play("Victory");await hero.play("Faint",{hold:true});await eng.wait(.5)},
  };

  onResize();
  const NEED=["hero_cute",api.foes[0]&&api.foes[0].model,"arena_meadow"];
  // ready：主角＋第一隻怪物到齊；場景模型若再 2.5 秒內到就一起等，否則先用程式草原
  return{handlers:H,hero,ready:Promise.all([hero.ready,core]).then(()=>Promise.race([arenaP,new Promise(r=>setTimeout(r,2500))])),progress:()=>load.progress(NEED),
    onQuality(){lowArena();hero.setOutline(false);if(foe)foe.setOutline(false)},setSlow(){}};
}
