// 手機拍的書頁常常是歪的（而且越下面歪得越多）：先估出文字列的傾斜角度，把整頁轉正再交給 OCR（兩個引擎共用）。
//   做法：縮小 → 灰階 → 去陰影找出墨水像素 → 橫向把字和字之間的小空隙補起來（一列字會連成一條長條）
//   → 找連通區塊 → 留下又長又扁的（文字列） → 用二階矩算每一條的角度 → 依長度加權取中位數。
//   每一條的位置與角度也一起回傳（lines），版面解析可以拿來把殘留的傾斜拉平。
// 只轉 0.3°–20°：更小的不值得重新取樣，更大的通常是估錯。
export function skewLines(canvas){const k=Math.min(1,1000/Math.max(canvas.width,canvas.height)),w=Math.max(8,Math.round(canvas.width*k)),h=Math.max(8,Math.round(canvas.height*k));
  const c=document.createElement("canvas");c.width=w;c.height=h;const g=c.getContext("2d",{willReadFrequently:true});g.drawImage(canvas,0,0,w,h);
  const d=g.getImageData(0,0,w,h).data,L=new Float32Array(w*h);for(let i=0;i<w*h;i++)L[i]=.3*d[i*4]+.59*d[i*4+1]+.11*d[i*4+2];
  const f=20,gw=Math.ceil(w/f),gh=Math.ceil(h/f),bg=new Float32Array(gw*gh);for(let y=0;y<h;y++)for(let x=0;x<w;x++){const gi=(y/f|0)*gw+(x/f|0);if(L[y*w+x]>bg[gi])bg[gi]=L[y*w+x]}
  const ink=new Uint8Array(w*h);for(let y=0;y<h;y++)for(let x=0;x<w;x++){const b=bg[(y/f|0)*gw+(x/f|0)];if(b>70&&L[y*w+x]<b*.62)ink[y*w+x]=1}
  // 橫向補空隙：同一列裡相隔不到 gap 的墨水連起來
  const gap=Math.max(3,Math.round(w*.012));for(let y=0;y<h;y++){let last=-1;for(let x=0;x<w;x++){if(ink[y*w+x]){if(last>=0&&x-last>1&&x-last<=gap)for(let t=last+1;t<x;t++)ink[y*w+t]=2;last=x}}}
  const seen=new Uint8Array(w*h),st=new Int32Array(w*h),out=[];
  for(let s=0;s<w*h;s++){if(!ink[s]||seen[s])continue;let top=0,n=0,sx=0,sy=0,sxx=0,syy=0,sxy=0,x0=w,x1=0,y0=h,y1=0;st[top++]=s;seen[s]=1;
    while(top){const i=st[--top],x=i%w,y=(i-x)/w;n++;sx+=x;sy+=y;sxx+=x*x;syy+=y*y;sxy+=x*y;if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;
      for(const j of [i-1,i+1,i-w,i+w])if(j>=0&&j<w*h&&ink[j]&&!seen[j]&&Math.abs((j%w)-x)<=1){seen[j]=1;st[top++]=j}}
    const bw=x1-x0+1,bh=y1-y0+1;if(bw<w*.05||bh>h*.08||n<20)continue;
    const mx=sx/n,my=sy/n,cxx=sxx/n-mx*mx,cyy=syy/n-my*my,cxy=sxy/n-mx*my,a=.5*Math.atan2(2*cxy,cxx-cyy);
    const l1=(cxx+cyy)/2+Math.sqrt(((cxx-cyy)/2)**2+cxy*cxy),l2=(cxx+cyy)/2-Math.sqrt(((cxx-cyy)/2)**2+cxy*cxy);
    if(l2<=0||l1/l2<25||Math.abs(a)>.42)continue;   // 夠細長（長寬比約 6 倍以上）而且接近水平
    out.push({x:mx/k,y:my/k,len:Math.sqrt(12*l1)/k,ang:a*180/Math.PI})}
  return out}
const wmedian=(arr)=>{const s=arr.slice().sort((a,b)=>a.ang-b.ang),tot=s.reduce((t,x)=>t+x.len,0);let acc=0;for(const x of s){acc+=x.len;if(acc>=tot/2)return x.ang}return 0};
export function skewAngle(canvas){const ls=skewLines(canvas);return ls.length<3?0:Math.round(wmedian(ls)*10)/10}

// 斜率場：把每一條文字列的斜率 tan(角度) 擬合成位置的二次多項式（u、v 是 -0.5～0.5 的頁面座標），
// 用長度加權的最小平方法，擬合三輪、每輪丟掉離群的（手寫字、旁邊另一頁的字）。條數太少就退回一次式或常數。
function solveLS(A,b){const n=b.length;for(let i=0;i<n;i++){let p=i;for(let r=i+1;r<n;r++)if(Math.abs(A[r][i])>Math.abs(A[p][i]))p=r;[A[i],A[p]]=[A[p],A[i]];[b[i],b[p]]=[b[p],b[i]];if(Math.abs(A[i][i])<1e-12)return null;
  for(let r=i+1;r<n;r++){const f=A[r][i]/A[i][i];for(let c=i;c<n;c++)A[r][c]-=f*A[i][c];b[r]-=f*b[i]}}const x=Array(n);for(let i=n-1;i>=0;i--){let t=b[i];for(let c=i+1;c<n;c++)t-=A[i][c]*x[c];x[i]=t/A[i][i]}return x}
const TERMS=[[(u,v)=>1],[(u,v)=>1,(u,v)=>u,(u,v)=>v],[(u,v)=>1,(u,v)=>u,(u,v)=>v,(u,v)=>u*v,(u,v)=>v*v,(u,v)=>u*u]];
export function slopeField(lines,W,H){let use=lines.map(l=>({u:l.x/W-.5,v:l.y/H-.5,s:Math.tan(l.ang*Math.PI/180),w:l.len}));if(use.length<3)return null;
  let coef=null,T=null;
  for(let round=0;round<3;round++){T=TERMS[use.length>=14?2:use.length>=6?1:0];const m=T.length,A=Array.from({length:m},()=>Array(m).fill(0)),b=Array(m).fill(0);
    for(const p of use){const f=T.map(t=>t(p.u,p.v));for(let i=0;i<m;i++){b[i]+=p.w*f[i]*p.s;for(let j=0;j<m;j++)A[i][j]+=p.w*f[i]*f[j]}}
    coef=solveLS(A,b);if(!coef)return null;const ev=p=>T.reduce((t,f,i)=>t+coef[i]*f(p.u,p.v),0);
    const res=use.map(p=>Math.abs(ev(p)-p.s)),rm=Math.sqrt(res.reduce((t,r,i)=>t+r*r*use[i].w,0)/use.reduce((t,p)=>t+p.w,0)),lim=Math.max(.035,2.5*rm);
    const next=use.filter((p,i)=>res[i]<=lim);if(next.length===use.length||next.length<3)break;use=next}
  const Tf=T,c=coef;return{f:(x,y)=>{const u=x/W-.5,v=y/H-.5;let s=0;for(let i=0;i<Tf.length;i++)s+=c[i]*Tf[i](u,v);return s>.4?.4:s<-.4?-.4:s},n:use.length,terms:Tf.length}}

// 回傳 {canvas, info}：沿著文字列的方向把每一列拉平（x 不動，只重新對應 y）。
// 目的列 y 從頁面中間那一行出發，往左右沿著斜率場一步一步走，走到的來源 y 就是這一列在原圖上的位置。歪得很少就原圖照用。
export async function straighten(canvas){let t0=performance.now();const brk=async()=>{if(performance.now()-t0>40){await new Promise(r=>setTimeout(r,0));t0=performance.now()}};
  const W=canvas.width,H=canvas.height,ls=skewLines(canvas),info={lines:ls.length,angle:ls.length<3?0:Math.round(wmedian(ls)*10)/10,warped:false};
  const F=slopeField(ls,W,H);if(!F)return{canvas,info};info.used=F.n;info.terms=F.terms;
  // 頁面上幾個點的角度（看歪多少）；全都在 0.3° 以內就不處理
  let mx=0;for(let y=.1;y<1;y+=.2)for(let x=.1;x<1;x+=.2)mx=Math.max(mx,Math.abs(F.f(x*W,y*H)));info.maxDeg=Math.round(Math.atan(mx)*1800/Math.PI)/10;
  if(mx<.005)return{canvas,info};
  const sd=canvas.getContext("2d",{willReadFrequently:true}).getImageData(0,0,W,H).data,out=document.createElement("canvas");out.width=W;out.height=H;
  const ctx=out.getContext("2d"),im=ctx.createImageData(W,H),o=im.data,xc=W>>1,sy=new Float32Array(W);
  for(let yd=0;yd<H;yd++){if(!(yd&31))await brk();
    let y=yd;for(let x=xc;x<W;x++){sy[x]=y;y+=F.f(x+.5,y)}y=yd;for(let x=xc-1;x>=0;x--){y-=F.f(x+.5,y);sy[x]=y}
    for(let x=0;x<W;x++){const j=(yd*W+x)*4,yy=sy[x];if(yy<0||yy>H-1.001){o[j]=o[j+1]=o[j+2]=255;o[j+3]=255;continue}
      const y0=yy|0,fy=yy-y0,i0=(y0*W+x)*4,i1=i0+W*4;for(let c=0;c<3;c++)o[j+c]=sd[i0+c]*(1-fy)+sd[i1+c]*fy;o[j+3]=255}}
  ctx.putImageData(im,0,0);info.warped=true;return{canvas:out,info}}
