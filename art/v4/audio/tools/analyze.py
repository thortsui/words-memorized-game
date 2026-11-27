# 讀音檔（用 ffmpeg 解成 PCM，不執行下載物），列出：長度、峰值時間、有效長度、頻譜重心、低頻比例
import subprocess, sys, numpy as np
SR=22050
def load(p):
    b=subprocess.run(["ffmpeg","-nostdin","-v","error","-i",p,"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout
    return np.frombuffer(b,dtype=np.float32)
for p in sys.argv[1:]:
    x=load(p)
    if len(x)<100: print(p,"EMPTY");continue
    w=512; n=len(x)//w; e=np.sqrt((x[:n*w].reshape(n,w)**2).mean(1)+1e-12); db=20*np.log10(e/e.max())
    act=np.where(db>-30)[0]; on=act[0]*w/SR; off=(act[-1]+1)*w/SR
    S=np.abs(np.fft.rfft(x*np.hanning(len(x)))); f=np.fft.rfftfreq(len(x),1/SR)
    cen=(S*f).sum()/S.sum(); low=S[f<300].sum()/S.sum(); hi=S[f>4000].sum()/S.sum()
    print(f"{p.split('/')[-1]:32s} dur={len(x)/SR:5.2f} on={on:4.2f} off={off:4.2f} pk={np.argmax(e)*w/SR:4.2f} cen={cen:6.0f} low={low:4.2f} hi={hi:4.2f}")
