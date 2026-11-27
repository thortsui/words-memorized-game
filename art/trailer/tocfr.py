# 螢幕串流的 jpg（不固定幀率）→ 30fps mp4；輸出起點時間（毫秒）
import os,sys,subprocess,json
d=sys.argv[1]; fs=sorted(f for f in os.listdir(d) if f.endswith('.jpg'))
ts=[int(f.split('_')[1][:-4]) for f in fs]
with open(d+'/list.txt','w') as o:
    for i,f in enumerate(fs):
        du=(ts[i+1]-ts[i])/1000 if i+1<len(fs) else .04
        o.write(f"file '{f}'\nduration {du:.4f}\n")
    o.write(f"file '{fs[-1]}'\n")
subprocess.run(['ffmpeg','-loglevel','error','-y','-f','concat','-safe','0','-i',d+'/list.txt','-vf','fps=30,format=yuv420p','-c:v','libx264','-crf','14','-preset','fast',d+'.mp4'],check=True)
json.dump({'t0':ts[0],'n':len(fs),'dur':(ts[-1]-ts[0])/1000},open(d+'.json','w')); print(d,ts[0],(ts[-1]-ts[0])/1000)
