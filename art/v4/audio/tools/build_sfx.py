# 單字魂音效建置：從 art/v4/audio/raw 的 CC0 取樣（只用 ffmpeg 讀取，不執行任何下載物）
# 疊層、變調、剪短、峰值正規化，輸出 mono mp3 到 public/sfx/
# 用法（專案根目錄）：python -P art/v4/audio/tools/build_sfx.py [名字 ...]
import subprocess, os, re, json, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..",".."))
RAW=os.path.join(ROOT,"art","v4","audio","raw"); OUT=os.path.join(ROOT,"public","sfx"); TMP=os.path.join(ROOT,"art","v4","audio","tmp")
os.makedirs(OUT,exist_ok=True); os.makedirs(TMP,exist_ok=True)
K="impact-sounds/Audio/"; KR="rpg-audio/Audio/"; C="creature/"; P="rpgpack/RPG Sound Pack/"; S="sword/"; SN="sword/sword - StarNinjas/"; O="oga100/"; B="breaking/"
VERB="aecho=0.8:0.6:70|150|260|420:0.32|0.24|0.16|0.1"   # 石室殘響
BIGVERB="aecho=0.85:0.7:90|190|330|520|760:0.35|0.28|0.2|0.13|0.08"
SHORTVERB="aecho=0.8:0.5:60|140:0.25|0.15"
def L(p,r=1.0,g=0,d=0,f=""): return dict(p=p,r=r,g=g,d=d,f=f)
R={
 # 金屬碰撞：劍砍甲
 "clash1":dict(L=[L(S+"sword_clash.2.ogg")],len=.55),
 "clash2":dict(L=[L(S+"sword_clash.4.ogg"),L(K+"impactPlate_medium_003.ogg",.9,-8)],len=.55),
 "clash3":dict(L=[L(S+"sword_clash.8.ogg",.94)],len=.5),
 "clash4":dict(L=[L(S+"sword_clash.7.ogg",1.05),L(K+"impactMetal_heavy_000.ogg",1,-6)],len=.55),
 # 重金屬撞擊（重擊／Boss 兵器相交）
 "clashBig1":dict(L=[L(S+"sword_clash.1.ogg",.85),L(K+"impactPlate_heavy_001.ogg",.8,-2),L(P+"inventory/metal-ringing.wav",.7,-8,30)],post=VERB,len=1.1),
 "clashBig2":dict(L=[L(S+"sword_clash.3.ogg",.8),L(K+"impactMetal_heavy_001.ogg",.75,-2),L(O+"metal_08.ogg",.8,-6)],post=VERB,len=1.1),
 # 彈反：清亮的「鏘」
 "parry1":dict(L=[L(S+"sword_clash.5.ogg",1.08),L(O+"bell_02.ogg",1.2,-9,10)],post=SHORTVERB,len=.8),
 "parry2":dict(L=[L(S+"sword_clash.10.ogg",1.12),L(P+"inventory/metal-ringing.wav",1.15,-6,10)],post=SHORTVERB,len=.8),
 # 揮劍破風
 "swingL1":dict(L=[L(P+"battle/swing.wav")],len=.3),
 "swingL2":dict(L=[L(P+"battle/swing2.wav",.95)],len=.25),
 "swingL3":dict(L=[L(P+"battle/swing3.wav",1.05)],len=.25),
 "swingL4":dict(L=[L(SN+"sword.6.ogg",.9,-2)],len=.35),
 "swingL5":dict(L=[L(SN+"sword.4.ogg",.85,-2)],len=.4),
 "swingH1":dict(L=[L(P+"battle/swing.wav",.62),L(P+"battle/swing3.wav",.7,-4,40)],post="lowpass=f=3500",len=.5),
 "swingH2":dict(L=[L(P+"battle/swing2.wav",.55),L(SN+"sword.5.ogg",.8,-10)],post="lowpass=f=3000",len=.55),
 "swingH3":dict(L=[L(SN+"sword.3.ogg",.62),L(P+"battle/swing.wav",.6,-3,60)],post="lowpass=f=3200",len=.6),
 # 砍中：肉／石
 "flesh1":dict(L=[L(K+"impactPunch_heavy_000.ogg"),L(KR+"chop.ogg",.9,-4)],len=.45),
 "flesh2":dict(L=[L(K+"impactPunch_heavy_002.ogg",.95),L(KR+"knifeSlice.ogg",1.1,-8)],len=.45),
 "flesh3":dict(L=[L(K+"impactPunch_heavy_004.ogg",.9),L(KR+"chop.ogg",.8,-5)],len=.45),
 "stone1":dict(L=[L(B+"bfh1_rock_breaking_02.ogg"),L(K+"impactMining_000.ogg",.9,-6)],len=.7),
 "stone2":dict(L=[L(B+"bfh1_rock_breaking_03.ogg",.9),L(K+"impactMining_004.ogg",.85,-5)],len=.7),
 # 格擋盾響
 "block1":dict(L=[L(K+"impactPlate_heavy_001.ogg",.85),L(K+"impactWood_heavy_000.ogg",.8,-5)],post=SHORTVERB,len=.6),
 "block2":dict(L=[L(K+"impactPlate_heavy_003.ogg",.8),L(K+"impactWood_heavy_002.ogg",.75,-5)],post=SHORTVERB,len=.6),
 # 翻滾布料
 "roll1":dict(L=[L(P+"inventory/cloth-heavy.wav",.9),L(P+"inventory/chainmail1.wav",1,-10,60),L(K+"impactSoft_heavy_001.ogg",.8,-10,180)],len=.6),
 "roll2":dict(L=[L(KR+"cloth1.ogg",.9),L(P+"inventory/chainmail2.wav",1,-12,40),L(K+"impactSoft_heavy_003.ogg",.8,-10,200)],len=.6),
 # 主角腳步
 "footstep1":dict(L=[L(KR+"footstep00.ogg")],len=.25),
 "footstep2":dict(L=[L(KR+"footstep01.ogg")],len=.25),
 "footstep3":dict(L=[L(KR+"footstep03.ogg")],len=.25),
 "footstep4":dict(L=[L(KR+"footstep06.ogg")],len=.25),
 # Boss 重踏
 "stomp1":dict(L=[L(K+"impactSoft_heavy_000.ogg",.55),L(O+"slam_03.ogg",.6,-6),L(B+"bfh1_rock_falling_04.ogg",.8,-12,40)],post="lowpass=f=2200,"+VERB,len=.9),
 "stomp2":dict(L=[L(K+"impactSoft_heavy_002.ogg",.5),L(O+"metal_10.ogg",.6,-9),L(B+"bfh1_rock_falling_07.ogg",.8,-12,30)],post="lowpass=f=2000,"+VERB,len=.9),
 # 重砸地／爆裂
 "slam1":dict(L=[L(O+"explosion.ogg",.6),L(B+"bfh1_rock_breaking_01.ogg",.8,-3,20),L(K+"impactSoft_heavy_004.ogg",.5,-2)],post="lowpass=f=4000,"+BIGVERB,len=1.6),
 "slam2":dict(L=[L(O+"slam_02.ogg",.55),L(B+"bfh1_rock_breaking_02.ogg",.75,-3,30),L(K+"impactMining_002.ogg",.6,-4)],post="lowpass=f=3800,"+BIGVERB,len=1.5),
 # 五隻 Boss 咆哮（同類素材變調疊加做出區別）
 "roar_sentinel":dict(L=[L(P+"NPC/giant/giant2.wav",.72),L(P+"NPC/giant/giant5.wav",.66,-4,120),L(B+"bfh1_metal_falling_01.ogg",.55,-10,60)],post="lowpass=f=2600,"+BIGVERB,len=2.0),
 "roar_gargoyle":dict(L=[L(C+"scream_01.ogg",.86),L(C+"monster_02.ogg",.8,-5,60),L(B+"bfh1_rock_falling_01.ogg",.7,-12,200)],post="highpass=f=180,"+VERB,len=1.7),
 "roar_priest":dict(L=[L(P+"NPC/shade/shade8.wav",.78),L(P+"NPC/shade/shade9.wav",.66,-3,260),L(P+"NPC/shade/shade12.wav",.9,-8,520)],post="chorus=0.6:0.9:50|70:0.4|0.32:0.25|0.4:2|1.3,lowpass=f=3500,"+BIGVERB,len=2.6),
 "roar_executioner":dict(L=[L(P+"NPC/gutteral beast/mnstr14.wav",.72),L(P+"NPC/gutteral beast/mnstr5.wav",.62,-3,90),L(C+"troll_01.ogg",.7,-6,40)],post="lowpass=f=3000,"+VERB,len=1.8),
 "roar_devourer":dict(L=[L(C+"monster_04.ogg",.8),L(C+"roar_02.ogg",.62,-2,60),L(C+"monster_07.ogg",.7,-3,200),L(C+"scream_02.ogg",.6,-9,120),L(P+"NPC/giant/giant2.wav",.55,-5,350)],post=BIGVERB,len=2.6),
 "roar1":dict(L=[L(C+"roar_02.ogg",.8),L(P+"NPC/giant/giant5.wav",.75,-5,60)],post=VERB,len=1.5),
 # Boss 死亡、階段轉換
 "bossDie":dict(L=[L(C+"monster_07.ogg",.6),L(P+"NPC/giant/giant4.wav",.5,-5,250),L(B+"bfh1_rock_falling_04.ogg",.7,-6,900),L(B+"bfh1_metal_falling_02.ogg",.7,-8,1100)],post="lowpass=f=3200,"+BIGVERB,len=3.0),
 "phase":dict(L=[L(O+"gong_02.ogg",.62),L(C+"monster_04.ogg",.6,-4,80),L(O+"explosion.ogg",.5,-8)],post="lowpass=f=2500,"+BIGVERB,len=3.0),
 # 喝藥
 "drink":dict(L=[L(P+"inventory/bottle.wav"),L(P+"inventory/bubble.wav",.85,-6,260),L(P+"inventory/bubble2.wav",.8,-8,480)],len=1.0),
 # 判定音
 "gradePerfect":dict(L=[L(O+"bell_01.ogg"),L(K+"impactBell_heavy_004.ogg",1.5,-10)],len=1.2),
 "gradeNormal":dict(L=[L(K+"impactMetal_light_002.ogg",1.1)],len=.25),
 "gradeWrong":dict(L=[L(K+"impactSoft_heavy_000.ogg",.7),L(O+"metal_10.ogg",.55,-10)],post="lowpass=f=900",len=.5),
 # 連段蓄勢、終結重擊
 "charge":dict(L=[L(P+"battle/sword-unsheathe3.wav",.9),L(P+"battle/magic1.wav",.6,-10,80)],post=SHORTVERB,len=1.0),
 "finisher":dict(L=[L(S+"sword_clash.1.ogg",.78),L(O+"explosion.ogg",.55,-2,10),L(K+"impactPunch_heavy_001.ogg",.7,-3),L(P+"inventory/metal-ringing.wav",.6,-8,40)],post=BIGVERB,len=2.0),
 # 冰／暗屬性
 "ice":dict(L=[L(B+"bfh1_glass_breaking_02.ogg",.8),L(K+"impactGlass_heavy_001.ogg",.7,-4)],post=SHORTVERB,len=1.0),
 "dark":dict(L=[L(P+"battle/spell.wav",.6),L(P+"NPC/shade/shade6.wav",.6,-6,200)],post="lowpass=f=2500,"+VERB,len=2.0),
 # 主角受擊（舊名 hurt）、介面小提示（舊名 shot）
 "hurt1":dict(L=[L(K+"impactPunch_medium_000.ogg",.9),L(P+"inventory/chainmail1.wav",1,-6,20)],len=.5),
 "hurt2":dict(L=[L(K+"impactPunch_medium_003.ogg",.85),L(P+"inventory/armor-light.wav",1,-6,20)],len=.5),
 "tick":dict(L=[L(K+"impactMetal_light_004.ogg",1.25,-3)],len=.2),
 # 配樂偶爾的遠鐘（BGM 用，音量由程式壓很小）
 "bell":dict(L=[L(O+"bell_03.ogg",.5),L(O+"gong_01.ogg",.5,-8)],post="lowpass=f=2500,"+BIGVERB,len=3.0),
}
def run(a): return subprocess.run(a,capture_output=True,text=True,encoding="utf-8",errors="replace")
def build(name,rc):
    ins=[];parts=[];labels=[]
    for i,l in enumerate(rc["L"]):
        ins+=["-i",os.path.join(RAW,l["p"])]
        ch=f"[{i}:a]aformat=channel_layouts=mono,aresample=44100,silenceremove=start_periods=1:start_threshold=-40dB"
        if l["r"]!=1: ch+=f",asetrate={int(44100*l['r'])},aresample=44100"
        if l["d"]: ch+=f",adelay={l['d']}"
        if l["g"]: ch+=f",volume={l['g']}dB"
        if l["f"]: ch+=","+l["f"]
        parts.append(ch+f"[a{i}]"); labels.append(f"[a{i}]")
    n=len(labels); ln=rc["len"]; fade=min(.25,ln*.4)
    mix=("".join(labels)+f"amix=inputs={n}:normalize=0:duration=longest") if n>1 else labels[0]+"anull"
    post=rc.get("post","")
    g=";".join(parts)+";"+mix+",apad=pad_dur=3"+(","+post if post else "")+f",atrim=0:{ln},afade=t=out:st={ln-fade:.3f}:d={fade:.3f}[o]"
    wav=os.path.join(TMP,name+".wav")
    r=run(["ffmpeg","-nostdin","-y","-v","error"]+ins+["-filter_complex",g,"-map","[o]","-ac","1","-ar","44100",wav])
    if r.returncode: print(name,"FAIL",r.stderr[-600:]); return None
    m=re.search(r"max_volume: (-?[\d.]+)",run(["ffmpeg","-nostdin","-i",wav,"-af","volumedetect","-f","null","-"]).stderr)
    gain=-1.0-float(m.group(1)); br="64k" if ln>=1.5 else "80k"
    mp3=os.path.join(OUT,name+".mp3")
    r=run(["ffmpeg","-nostdin","-y","-v","error","-i",wav,"-af",f"volume={gain:.2f}dB,alimiter=limit=0.95","-ac","1","-ar","44100","-c:a","libmp3lame","-b:a",br,mp3])
    if r.returncode: print(name,"ENC FAIL",r.stderr[-400:]); return None
    return os.path.getsize(mp3)
only=sys.argv[1:]
for k,v in R.items():
    if only and k not in only: continue
    s=build(k,v)
    if s: print(f"{k:18s} {v['len']:4.1f}s {s/1024:6.1f}KB")
print("total KB",round(sum(os.path.getsize(os.path.join(OUT,f)) for f in os.listdir(OUT) if f.endswith('.mp3'))/1024,1))
json.dump({k:[dict(file=l["p"],rate=l["r"],gainDb=l["g"],delayMs=l["d"]) for l in v["L"]] for k,v in R.items()},open(os.path.join(TMP,"recipes.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
