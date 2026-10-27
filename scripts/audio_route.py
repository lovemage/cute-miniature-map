# 代码合成配音：城市底噪 + 机车掠过 + 景点出现的木琴“叮” + 鸟鸣 + （可选）和弦与拨弦旋律
# 用法：python audio.py            → audio.wav（完整配乐）
#       python audio.py --sfx      → sfx.wav（只有音效，用来叠外部背景音乐）
# 景点出现时间从 meta.json 读取（render.js 导出），与画面卡片弹出对齐
import numpy as np, wave, sys, json
from scipy.signal import lfilter
SFX_ONLY = '--sfx' in sys.argv
META = json.load(open('meta.json', encoding='utf-8'))
SR = 44100; DUR = META['dur']; n = int(SR * DUR); t = np.arange(n) / SR; rng = np.random.default_rng(3)
L = np.zeros(n); Rch = np.zeros(n)
def add(sig, start, gain=1.0, pan=0.0):
    k = int(max(0, start) * SR); m = min(len(sig), n - k)
    if m <= 0: return
    L[k:k+m] += sig[:m] * gain * np.sqrt((1 - pan) / 2) * 1.414
    Rch[k:k+m] += sig[:m] * gain * np.sqrt((1 + pan) / 2) * 1.414
lp = lambda x, a: lfilter([a], [1, a - 1], x)

# 城市底噪：远处车流（低通噪声，缓慢起伏）
for ch in (L, Rch):
    ch += lp(rng.standard_normal(n), 0.012) * 0.10 * (1 + 0.25 * np.sin(2 * np.pi * 0.07 * t + rng.uniform(0, 6)))

# 机车掠过：带多普勒下滑的嗡声，左右平移
for s in rng.uniform(1, DUR - 3, 7):
    m = int(2.2 * SR); tt = np.arange(m) / SR; f = 105 + 25 * np.tanh((1.1 - tt) * 2.5)
    buzz = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.5 + np.sin(4 * np.pi * np.cumsum(f) / SR) * 0.3
    env = np.exp(-((tt - 1.1) / 0.45) ** 2)
    sig = lp(buzz, 0.08) * env; d = rng.choice([-1, 1])
    for j in range(4):   # 分段平移，模拟从一侧开到另一侧
        a, b = j * m // 4, (j + 1) * m // 4; add(sig[a:b], s + a / SR, 0.05, d * (-0.8 + 0.53 * j))

# 景点出现：木琴“叮”，音高沿五声音阶一路往上走
PENTA = [523.25, 587.33, 659.26, 783.99, 880.0, 1046.5, 1174.66, 1318.51]
def marimba(f, d=0.9):
    tt = np.arange(int(d * SR)) / SR
    return (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 7) + 0.35 * np.sin(2 * np.pi * f * 4 * tt) * np.exp(-tt * 28)
            + 0.15 * np.sin(2 * np.pi * f * 10 * tt) * np.exp(-tt * 60)) * np.minimum(1, tt / 0.002)
for k, tr in enumerate(META['reveals']):
    if tr < 0: tr = 0.25
    f = PENTA[min(k, len(PENTA) - 1)] if k < 8 else PENTA[(k - 8) % 5 + 3]
    add(marimba(f), tr, 0.16); add(marimba(f * 1.5), tr + 0.09, 0.07)

# 鸟鸣（与画面飞鸟时段大致对应）
for s in np.concatenate([rng.uniform(0.5, 11, 5), rng.uniform(11, 23, 5), rng.uniform(20, DUR - 1, 4)]):
    m = int(0.11 * SR); tt = np.arange(m) / SR; f = rng.uniform(2900, 3600) - 9000 * tt
    add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / 0.11), s, 0.05, rng.uniform(-.8, .8))

if not SFX_ONLY:
    # 和弦铺底 C → Am → F → G 循环（每 3.75 秒一个），最后回到 C
    CH = [(130.81, 196.0, 261.63, 329.63), (110.0, 164.81, 220.0, 261.63), (87.31, 130.81, 220.0, 261.63), (98.0, 146.83, 246.94, 293.66)]
    SEG = 3.75; nseg = int(np.ceil(DUR / SEG)); pad = np.zeros(n)
    for k in range(nseg):
        chord = CH[k % 4] if k < nseg - 1 else CH[0]
        a, b = k * SEG - 0.5, (k + 1) * SEG + 0.5
        env = np.clip(np.minimum((t - a) / 1.0, (b - t) / 1.0), 0, 1); env = 0.5 - 0.5 * np.cos(np.pi * env)
        for j, f in enumerate(chord): pad += env * 0.03 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t + j))
    add(pad * np.minimum(1, t / 1.5) * np.minimum(1, (DUR - t) / 2), 0)
    # 轻快拨弦：八分音符网格上按和弦取五声音阶音
    def pluck(f, d=1.4):
        tt = np.arange(int(d * SR)) / SR
        return sum(np.sin(2 * np.pi * f * h * tt) / h ** 1.3 * np.exp(-tt * (3 + 2.2 * h)) for h in range(1, 6)) * np.minimum(1, tt / 0.004)
    NOTES = {0: [261.63, 329.63, 392.0, 523.25], 1: [220.0, 261.63, 329.63, 440.0], 2: [261.63, 349.23, 440.0, 523.25], 3: [293.66, 392.0, 493.88, 587.33]}
    step = SEG / 8
    for i in range(int((DUR - 2.5) / step)):
        if rng.random() < (0.85 if i % 2 == 0 else 0.35):
            k = int(i * step // SEG) % 4; add(pluck(rng.choice(NOTES[k])), 0.4 + i * step, 0.055, rng.uniform(-.3, .3))

st = np.stack([L, Rch], 1)
st *= (np.minimum(1, t / 0.3) * np.minimum(1, (DUR - t) / 1.5))[:, None]
st = np.int16(np.clip(st / np.abs(st).max() * 0.85, -1, 1) * 32767)
OUT = 'sfx.wav' if SFX_ONLY else 'audio.wav'
with wave.open(OUT, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
print(OUT, DUR, 's')
