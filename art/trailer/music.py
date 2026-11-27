import numpy as np, json, wave
SR=44100; T=json.load(open('tl.json')); N=int(T['total']*SR); L=np.zeros(N); R=np.zeros(N)
rng=np.random.default_rng(3)
def add(sig,t,pan=0.,g=1.):
    i=int(t*SR); n=min(len(sig),N-i)
    if n<=0: return
    L[i:i+n]+=sig[:n]*g*(1-pan)/1; R[i:i+n]+=sig[:n]*g*(1+pan)/1
def env(n,a,d):
    t=np.arange(n)/SR; return np.minimum(1,t/max(a,1e-4))*np.exp(-t/d)
def lp(x,a):  # one-pole lowpass (vectorised via cumulative trick is hard; use FFT)
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/SR); X*=1/(1+(f/a)**4); return np.fft.irfft(X,len(x))
def hz(m): return 440*2**((m-69)/12)
def pluck(m,dur=2.2,b=.996):
    p=int(SR/hz(m)); buf=rng.uniform(-1,1,p); out=np.zeros(int(dur*SR))
    # Karplus-Strong 向量化：每次處理一個週期
    y=buf.copy(); i=0
    while i<len(out):
        n=min(p,len(out)-i); out[i:i+n]=y[:n]; y=b*.5*(y+np.roll(y,-1)); i+=p
    bend=1; return out*env(len(out),.002,dur*.45)*1.2
def taiko(g=1.,low=1.):
    n=int(1.6*SR); t=np.arange(n)/SR; f=48*low+70*np.exp(-t*18); ph=2*np.pi*np.cumsum(f)/SR
    body=np.sin(ph)*np.exp(-t*3.2); hit=lp(rng.normal(0,1,n),900)*np.exp(-t*40)*.8
    return (body+hit)*g
def gong(dur=9.):
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for f,a,d in [(92,1,6),(161,.7,5),(237,.5,4),(331,.35,3),(447,.25,2.4),(613,.18,1.6),(877,.1,1.2)]:
        s+=a*np.sin(2*np.pi*f*t*(1+.002*np.sin(2*np.pi*.7*t)))*np.exp(-t/d)
    return s*np.minimum(1,t/.02)*.5
def saw(m,dur,det=(0,.07,-.07)):
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for d in det: f=hz(m+d); s+=2*((t*f)%1)-1
    return s/len(det)
def drone(ms,t0,t1,a=2.,r=2.,g=.12,cut=500):
    dur=t1-t0; s=sum(saw(m,dur) for m in ms)/len(ms); s=lp(s,cut); n=len(s); t=np.arange(n)/SR
    e=np.minimum(1,t/a)*np.minimum(1,(dur-t)/r).clip(0); add(s*e,t0,g=g*2.0)
def stab(ms,t,g=.35):
    s=sum(saw(m,1.8) for m in ms)/len(ms); s=lp(s,700)*env(len(s),.01,.5); add(s,t,g=g)
def shing(t,g=.25):
    n=int(1.2*SR); x=rng.normal(0,1,n); X=np.fft.rfft(x); f=np.fft.rfftfreq(n,1/SR); X*=np.exp(-((f-6500)/1800)**2); s=np.fft.irfft(X,n)
    s=s/np.abs(s).max()*env(n,.005,.25); add(s,t,.3,g)
def riser(t0,t1,g=.3):
    n=int((t1-t0)*SR); x=rng.normal(0,1,n); k=np.linspace(0,1,n)
    s=lp(x,4000)*k**2; add(s,t0,g=g)
def wind(t0,t1,g=.05):
    n=int((t1-t0)*SR); s=lp(rng.normal(0,1,n),400); s*=0.6+0.4*np.sin(np.linspace(0,7,n)); e=np.minimum(1,np.arange(n)/SR/1.5)*np.minimum(1,(t1-t0-np.arange(n)/SR)/1.5); add(s*e,t0,g=g*2.0)
D=50 # D3
pent=[0,3,5,7,10,12,15,17]
# 開場：風聲＋古箏
wind(0,16,.12)
for t,k,p in [(0.8,4,-.3),(1.5,3,.2),(2.0,2,-.1),(3.2,1,.3),(4.0,0,-.2),(5.6,2,.1),(6.2,4,.3)]: add(pluck(D+12+pent[k]),t,p,.55)
# 封面：低音弦樂鋪底
drone([D-12,D-5],7,18,a=3,r=1,g=.16,cut=420)
for t,k in [(8.5,5),(9.3,4),(10.8,3),(12.6,2),(13.2,1)]: add(pluck(D+12+pent[k]),t,.2,.4)
for t in [11,13]: add(taiko(.5),t)
# 每答出一個字
add(taiko(1.2),15.0); add(taiko(1.4,.8),T['n5']); stab([D-12,D-5,D],T['n5'],.3); shing(T['n5']+.05,.18)
# Boss 段：鼓點節奏＋每隻 Boss 一記重擊
drone([D-12,D-9,D-5],18,43.5,a=1,r=1.5,g=.13,cut=380)
chords=[[D-12,D-5],[D-11,D-4],[D-14,D-7],[D-9,D-2],[D-12,D-7,D-5]]
for i,b in enumerate(T['boss']):
    add(taiko(1.4,.8),b); stab([m for m in chords[i]],b,.32); shing(b+.6,.15)
    for k in range(1,5): add(taiko(.45 if k%2 else .6),b+k)
    if i==4: [add(taiko(.5),b+4+j*.25) for j in range(4)]
# 對決：出題時滴答聲，選擇時一聲，答對＝鼓＋金屬聲，答錯＝不和諧重擊
drone([D-12,D-11],T['duel'],T['mont']+.2,a=.3,r=.4,g=.09,cut=500)
def tick(t,g=.2):
    n=int(.05*SR); s=np.sin(2*np.pi*2400*np.arange(n)/SR)*np.exp(-np.arange(n)/SR*90); add(s,t,.2,g)
for b0,du,kind,hit,_ in T['beats']:
    for j in range(6): tick(b0+.1+j*.25,.18)
    tick(b0+1.6,.45); add(taiko(.5,1.3),b0+1.6)
    ht=b0+2.4+hit
    if kind=='ok': add(taiko(1.3),ht); shing(ht,.3); stab([D-12,D-5,D+2],ht,.28)
    else: add(taiko(1.6,.6),ht); stab([D-12,D-11,D-6],ht,.45); add(gong(3.)*.5,ht)
add(taiko(1.2),T['slogan']); stab([D-12,D-5,D],T['slogan'],.3)
# 剪輯高潮：每個剪接點一記鼓＋弦樂快速頓音
drone([D-12,D-5,D],T['mont'],T['black'],a=.2,r=.1,g=.15,cut=900)
for c in T['cuts']: add(taiko(1.1),c)
t=T['mont']
while t<T['black']-.1:
    s=saw(D-12,.12); s=lp(s,1200)*env(len(s),.003,.06); add(s,t,g=.35); t+=.125
for w in T['words']: shing(w[0],.22)
riser(T['black']-2.5,T['black'],.25)
# 收尾：停頓→銅鑼＋巨鼓
add(gong(),T['title']-.02,0,.9); add(taiko(1.8,.7),T['title']); stab([D-24,D-12,D-5],T['title'],.4)
drone([D-12,D-5],T['title'],T['total'],a=.1,r=5,g=.12,cut=350)
for j,k in enumerate([4,3,2,0]): add(pluck(D+12+pent[k],2.5),T['end']+.3+j*.7,(-1)**j*.2,.4)
# 混音：簡易殘響＋限制
def reverb(x):
    y=x.copy()
    for d,g in [(0.031,.35),(0.047,.3),(0.071,.25),(0.113,.2),(0.173,.15),(0.257,.1)]:
        k=int(d*SR); y[k:]+=x[:-k]*g
    return y
L=reverb(L); R=reverb(R[::-1])[::-1]*0+reverb(R)
m=max(np.abs(L).max(),np.abs(R).max()); L=np.tanh(L/m*2.6)/np.tanh(2.6); R=np.tanh(R/m*2.6)/np.tanh(2.6)
fade=np.minimum(1,(N-np.arange(N))/SR/2.5); L*=fade*.9; R*=fade*.9
d=(np.stack([L,R],1)*32767).astype(np.int16)
w=wave.open('music.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes()); w.close(); print('ok',N/SR)
