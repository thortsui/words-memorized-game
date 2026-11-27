import json,subprocess,os
T=json.load(open('tl.json')); os.makedirs('seg',exist_ok=True)
FPS=30
def run(a): subprocess.run(['ffmpeg','-loglevel','error','-y']+a,check=True)
# seg: (name, dur, src, src_start, overlays[(png,t_in,t_out,fade)], vfade_in, vfade_out, extra_vf)
def seg(name,dur,src=None,ss=0,ovs=(),fin=.0,fout=.0,place=None):
    ins=[];fc=[]
    if src: ins+=['-ss',str(ss),'-t',str(dur),'-i',src]
    else: ins+=['-f','lavfi','-t',str(dur),'-i',f'color=black:s=1920x1080:r={FPS}']
    base='[0:v]fps=30,format=yuv420p'
    if place:  # 縮放並擺在黑底上的指定位置
        ins+=['-f','lavfi','-t',str(dur),'-i',f'color=black:s=1920x1080:r={FPS}']
        w,x,y=place; fc.append(f'[0:v]fps=30,scale={w}:-2[s];[1:v][s]overlay={x}:{y},format=yuv420p[v0]'); k=2
    else: fc.append(base+'[v0]'); k=1
    cur='v0'
    for i,(png,a,b,f) in enumerate(ovs):
        ins+=['-loop','1','-t',str(dur),'-i',f'cards/{png}.png']
        fc.append(f'[{k}:v]format=rgba,fade=t=in:st={a}:d={f}:alpha=1,fade=t=out:st={b-f}:d={f}:alpha=1[o{i}]')
        fc.append(f'[{cur}][o{i}]overlay=0:0:enable=\'between(t,{a},{b})\'[c{i}]'); cur=f'c{i}'; k+=1
    fx=[]
    if fin: fx.append(f'fade=t=in:st=0:d={fin}')
    if fout: fx.append(f'fade=t=out:st={dur-fout}:d={fout}')
    fc.append(f'[{cur}]'+(','.join(fx) if fx else 'null')+',format=yuv420p[out]')
    run(ins+['-filter_complex',';'.join(fc),'-map','[out]','-r',str(FPS),'-c:v','libx264','-crf','14','-preset','fast','-an',f'seg/{name}.mp4'])
    return f'seg/{name}.mp4'
S=[];add=lambda *a,**k:S.append(seg(*a,**k))
# 0–7 開場旁白
add('a_open',7,ovs=[('n1',1.0,6.4,.9),('n2',2.6,6.4,.9)])
# 7–15 封面山水
add('b_cover',8,'raw_cover.mp4',3.5,ovs=[('n3',1.5,7.4,.8)],fin=1.2,fout=.6)
# 15–18 每答出一個字
add('c_hook',3,ovs=[('n4',.1,2.9,.25),('n5',1.5,2.9,.15)])
# 18–43 五隻 Boss 登場
for i,ss in enumerate([4.0,32.5,62.5,94.0,117.5]):
    add(f'd_boss{i+1}',5,'raw_soul.mp4',ss,ovs=[(f'boss{i+1}',.6,4.85,.35)],fin=.15,fout=.15)
# 實戰：手機直式真實遊玩畫面（右），左側階段字卡；背景是同畫面的模糊放大
def seg_phone(name,src,ss,dur,caps):
    ins=['-ss',str(ss),'-t',str(dur),'-i',src,'-loop','1','-t',str(dur),'-i','cards/bezel.png','-loop','1','-t',str(dur),'-i','cards/leftshade.png']
    fc=['[0:v]fps=30,split[a][b]','[a]scale=1920:-2,crop=1920:1080:0:(ih-1080)*0.38,boxblur=28:3,eq=brightness=-0.3:saturation=0.5[bg0]','[bg0][2:v]overlay=0:0[bg]',
        '[b]scale=461:1000[ph]','[bg][ph]overlay=1196:40[x0]','[x0][1:v]overlay=1180:24[c0]'];cur='c0'
    for i,(png,a,b_) in enumerate(caps):
        ins+=['-loop','1','-t',str(dur),'-i',f'cards/{png}.png'];k=i+3
        fc.append(f'[{k}:v]format=rgba,fade=t=in:st={a}:d=0.15:alpha=1,fade=t=out:st={b_-0.12}:d=0.12:alpha=1[o{i}]')
        fc.append(f"[{cur}][o{i}]overlay=0:0:enable='between(t,{a},{b_})'[c{i+1}]");cur=f'c{i+1}'
    fc.append(f'[{cur}]format=yuv420p[out]')
    run(ins+['-filter_complex',';'.join(fc),'-map','[out]','-r',str(FPS),'-c:v','libx264','-crf','14','-preset','fast','-an',f'seg/{name}.mp4'])
    return f'seg/{name}.mp4'
for n,(src,ss,du,caps,st) in enumerate(T['play']['clips']): S.append(seg_phone(f'e_p{n}',src,ss,du,caps))
add('e_slo',2.2,ovs=[('slogan',.1,2.15,.25)])
# 48–56 剪輯高潮
picks=[10.7,18.5,24.7,40.2,48.6,51.8,69.6,79.5,82.8,98.6,105.6,121.6,127.6,138.6]
cuts=T['cuts']+[T['black']]
words={round(w[0],2):w[1] for w in T['words']}
for j,ss in enumerate(picks):
    d=round(cuts[j+1]-cuts[j],3); ov=[]
    add(f'f_m{j:02d}',d,'raw_soul.mp4',ss)
# 文字閃卡（0.25 秒）插在高潮段中間：直接用黑底＋字卡疊在對應時間
# 56–57 黑
add('g_black',1)
# 57–65 標題
add('h_title',8,'raw_cover.mp4',13,ovs=[('title',.25,7.6,.6)],fin=.08,fout=.4)
# 65–69 片尾
add('i_end',4,ovs=[('end',.3,3.7,.5)])
with open('seg/list.txt','w') as f:
    for s in S: f.write(f"file '{os.path.basename(s)}'\n")
run(['-f','concat','-safe','0','-i','seg/list.txt','-c','copy','seg/joined.mp4'])
# 全片：字卡閃現、調色、顆粒、暗角、電影黑邊、配樂
ins=['-i','seg/joined.mp4']; fc=['[0:v]eq=contrast=1.07:saturation=.88:gamma=.98,colorbalance=rs=.03:bs=-.03:rh=.04:bh=-.04,vignette=PI/4.2,noise=alls=4:allf=t[g]']; cur='g'; k=1
for t,w in T['words']:
    ins+=['-loop','1','-t','0.4','-itsoffset',str(t),'-i',f'cards/{w}.png']
    fc.append(f"[{cur}]drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(t,{t},{t+.3})'[b{k}]")
    fc.append(f"[b{k}][{k}:v]overlay=0:0:eof_action=pass:enable='between(t,{t},{t+.3})'[w{k}]"); cur=f'w{k}'; k+=1
LB=f"enable='not(between(t,{T['play']['start']},{T['play']['end']}))'"
fc.append(f'[{cur}]drawbox=x=0:y=0:w=iw:h=132:color=black:t=fill:{LB},drawbox=x=0:y=ih-132:w=iw:h=132:color=black:t=fill:{LB},format=yuv420p[v]')
ins+=['-i','music.wav']
run(ins+['-filter_complex',';'.join(fc),'-map','[v]','-map',f'{k}:a','-c:v','libx264','-crf','21','-maxrate','7M','-bufsize','14M','-preset','slow','-profile:v','high','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest','單字魂_宣傳片.mp4'])
print('done')
