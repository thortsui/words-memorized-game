// 測試用：在現有 Boss GLB 加上 P2_/P3_ 型態節點（剛體，掛在頭部骨頭）與 Glow 材質；devourer 另複製 PhaseShift 為 PhaseShift2
import { NodeIO } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/@gltf-transform/core/dist/index.js';
import { ALL_EXTENSIONS } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/@gltf-transform/extensions/dist/index.js';
import { MeshoptDecoder } from 'file:///D:/Documents/ThorWorkSpace/Remamber%20word%20game/node_modules/meshoptimizer/index.js';
import fs from 'node:fs';
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const COL={sentinel:[.49,1,.69],gargoyle:[1,.54,.23],priest:[.56,.89,1],executioner:[.69,.48,1],devourer:[1,.23,.16]};
fs.mkdirSync('glb',{recursive:true});
for(const id of Object.keys(COL)){const doc=await io.read(`D:/Documents/ThorWorkSpace/Remamber word game/public/models/boss_${id}.glb`);const r=doc.getRoot();
  for(const e of r.listExtensionsUsed())if(/meshopt/i.test(e.extensionName))e.dispose();
  const buf=r.listBuffers()[0];const nodes=r.listNodes();
  // 高度：所有 mesh 節點 world bbox 粗估（取 skin joints 的 y 範圍）
  let ymin=1e9,ymax=-1e9;for(const n of nodes){const t=n.getWorldTranslation();ymin=Math.min(ymin,t[1]);ymax=Math.max(ymax,t[1])}const H=Math.max(.5,ymax-ymin);
  const head=nodes.find(n=>/head/i.test(n.getName())&&!n.getMesh())||nodes.find(n=>/neck|spine/i.test(n.getName()))||r.listScenes()[0].listChildren()[0];
  const ws=head.getWorldMatrix(),sc=Math.hypot(ws[0],ws[1],ws[2])||1;
  const box=(s,name,matName,color,shape='box')=>{const P=[],Nn=[],I=[];
    const faces=[[0,1,2,1],[0,1,2,-1],[1,2,0,1],[1,2,0,-1],[2,0,1,1],[2,0,1,-1]];
    for(const [a,b,c,sg] of faces){const base=P.length/3;for(const [u,v] of [[-1,-1],[1,-1],[1,1],[-1,1]]){const p=[0,0,0];p[a]=u*s[a];p[b]=v*s[b];p[c]=sg*s[c];P.push(...p);const nn=[0,0,0];nn[c]=sg;Nn.push(...nn)}
      if(sg>0)I.push(base,base+1,base+2,base,base+2,base+3);else I.push(base,base+2,base+1,base,base+3,base+2)}
    const pa=doc.createAccessor().setType('VEC3').setArray(new Float32Array(P)).setBuffer(buf),na=doc.createAccessor().setType('VEC3').setArray(new Float32Array(Nn)).setBuffer(buf),ia=doc.createAccessor().setType('SCALAR').setArray(new Uint16Array(I)).setBuffer(buf);
    const m=doc.createMaterial(matName).setBaseColorFactor([...color.map(x=>x*.3),1]).setEmissiveFactor(color).setRoughnessFactor(.6);
    const prim=doc.createPrimitive().setAttribute('POSITION',pa).setAttribute('NORMAL',na).setIndices(ia).setMaterial(m);return doc.createMesh(name).addPrimitive(prim)};
  const u=H*.09/sc;const c=COL[id];
  // P2：頭上一對「角」（scale 0 匯出）＋一個沒藏好的 P2（scale 1）
  const horns=doc.createNode('P2_TestHorns').setScale([0,0,0]).setTranslation([0,u*2.2,0]);
  for(const s of [-1,1])horns.addChild(doc.createNode('P2_TestHorn'+(s>0?'R':'L')).setMesh(box([u*.35,u*1.6,u*.35],'hornmesh','P2_Glow_Test',c)).setTranslation([s*u*1.4,u*1.2,0]).setRotation([0,0,Math.sin(-s*.25),Math.cos(.25)]));
  head.addChild(horns);
  head.addChild(doc.createNode('P2_TestUnhidden').setMesh(box([u*2.2,u*.25,u*.25],'barmesh','P2_Glow_Bar',c)).setTranslation([0,u*4.6,0]));
  if(id==='devourer'){const halo=doc.createNode('P3_TestHalo').setScale([0,0,0]).setTranslation([0,u*6,0]);for(let i=0;i<10;i++){const a=i/10*Math.PI*2;halo.addChild(doc.createNode('P3_TestHaloSeg'+i).setMesh(box([u*.45,u*.18,u*.18],'halomesh','P3_Glow_Halo',[1,.15,.1])).setTranslation([Math.cos(a)*u*2.6,0,Math.sin(a)*u*2.6]).setRotation([0,Math.sin(-a/2),0,Math.cos(-a/2)]))}head.addChild(halo);
    const ps=r.listAnimations().find(a=>a.getName()==='PhaseShift');if(ps){const a2=doc.createAnimation('PhaseShift2');for(const ch of ps.listChannels()){const s=ch.getSampler();const s2=doc.createAnimationSampler().setInput(s.getInput()).setOutput(s.getOutput()).setInterpolation(s.getInterpolation());a2.addSampler(s2).addChannel(doc.createAnimationChannel().setTargetNode(ch.getTargetNode()).setTargetPath(ch.getTargetPath()).setSampler(s2))}}}
  await io.write(`glb/boss_${id}.glb`,doc);console.log(id,'head=',head.getName(),'H=',H.toFixed(2),'sc=',sc.toFixed(3),fs.statSync(`glb/boss_${id}.glb`).size)}
