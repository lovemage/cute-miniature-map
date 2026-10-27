# 代码合成配音：风/水底噪 + 四段和弦铺底 + 五声音阶拨弦 + 寺院钟 + 鸟鸣 + 入水声 + 咖啡杯轻碰
# 时间点与 scene.html 对齐：每段 SEG=DUR/4 秒切换文案；RIPPLES 入水涟漪
import numpy as np, wave, sys
from scipy.signal import lfilter
args = [a for a in sys.argv[1:] if not a.startswith('--')]; SFX_ONLY = '--sfx' in sys.argv   # --sfx：只出音效，配外部背景音乐
SR = 44100; DUR = float(args[0]) if args else 15; SEG = DUR / 4
n = int(SR * DUR); t = np.arange(n) / SR; rng = np.random.default_rng(1)
L = np.zeros(n); Rch = np.zeros(n)
def add(sig, start, gain=1.0, pan=0.0):            # pan: -1 左 … +1 右
    k = int(start * SR); m = min(len(sig), n - k)
    if m <= 0: return
    L[k:k+m] += sig[:m] * gain * np.sqrt((1 - pan) / 2) * 1.414
    Rch[k:k+m] += sig[:m] * gain * np.sqrt((1 + pan) / 2) * 1.414
lp = lambda x, a: lfilter([a], [1, a - 1], x)       # 一阶低通

# 风 / 护城河水声底噪（左右声道去相关）
for ch in (L, Rch):
    ch += lp(rng.standard_normal(n), 0.02) * 0.09 * (1 + 0.3 * np.sin(2 * np.pi * 0.11 * t + rng.uniform(0, 6)))
    ch += lp(rng.standard_normal(n), 0.25) * 0.006   # 细碎水声

# 和弦铺底：D → Bm → Gmaj7 → Dadd9，每段一个和弦，余弦交叉淡化
CH = [(146.83, 220.00, 293.66, 369.99), (123.47, 185.00, 246.94, 293.66),
      (98.00, 146.83, 246.94, 369.99), (146.83, 220.00, 329.63, 369.99)]
pad = np.zeros(n)
for k, chord in enumerate(CH):
    a, b = k * SEG - 0.6, (k + 1) * SEG + 0.6
    env = np.clip(np.minimum((t - a) / 1.2, (b - t) / 1.2), 0, 1); env = 0.5 - 0.5 * np.cos(np.pi * env)
    for j, f in enumerate(chord):
        vib = 1 + 0.002 * np.sin(2 * np.pi * (4.5 + j * 0.3) * t)
        pad += env * 0.035 * (np.sin(2 * np.pi * f * vib * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t + j))
pad *= np.minimum(1, t / 1.5) * np.minimum(1, (DUR - t) / 1.5)
if not SFX_ONLY: add(pad, 0, 1.0)

# 拨弦（类似兰纳 sueng 琴）：衰减谐波叠加，D 大调五声音阶
def pluck(f, d=2.0):
    tt = np.arange(int(d * SR)) / SR
    s = sum(np.sin(2 * np.pi * f * h * tt) / h ** 1.3 * np.exp(-tt * (2.2 + 1.9 * h)) for h in range(1, 7))
    return s * np.minimum(1, tt / 0.004)
D4, E4, F4, A4, B4, D5, E5 = 293.66, 329.63, 369.99, 440.0, 493.88, 587.33, 659.26
MEL = [(.5, A4), (1.44, B4), (1.9, D5), (2.38, A4), (3.3, F4),
       (4.25, F4), (4.72, A4), (5.2, B4), (6.13, D5), (6.6, E5), (7.05, D5),
       (8.0, B4), (8.47, A4), (8.94, F4), (9.88, E4), (10.35, F4), (10.8, A4),
       (11.75, A4), (12.22, F4), (12.7, E4), (13.4, D4)]
for s, f in ([] if SFX_ONLY else MEL): add(pluck(f), s * DUR / 15, 0.09, rng.uniform(-.25, .25))

# 寺院钟：非谐波分音 + 轻微拍频，长衰减
def bell(f0, d=5.0):
    tt = np.arange(int(d * SR)) / SR; s = np.zeros_like(tt)
    for r, a, dec in [(1, 1, .9), (2.0, .5, 1.4), (2.76, .35, 2.0), (3.9, .2, 2.8), (5.4, .12, 4.0)]:
        s += a * (np.sin(2 * np.pi * f0 * r * tt) + np.sin(2 * np.pi * (f0 * r + .7) * tt)) / 2 * np.exp(-tt * dec)
    return s * np.minimum(1, tt / 0.003)
add(bell(146.83), 0.12, 0.22); add(bell(146.83), 13.0 * DUR / 15, 0.12)

# 段落切换的风铃闪音（与文案切换同步）
for k in (1, 2, 3):
    for j in range(6):
        tt = np.arange(int(1.2 * SR)) / SR; f = rng.uniform(2200, 3600)
        add(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 5), k * SEG - 0.1 + j * 0.06, 0.025, rng.uniform(-.6, .6))

# 鸟鸣：快速下滑 FM，最后一段更多
for s in np.concatenate([rng.uniform(0.8, DUR - 1, 9), rng.uniform(11.4, DUR - .8, 5)]):
    for rep in range(rng.integers(1, 3)):
        m = int(0.11 * SR); tt = np.arange(m) / SR; f = rng.uniform(2900, 3600) - 9000 * tt
        add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / 0.11), s + rep * 0.16, 0.07, rng.uniform(-.8, .8))

# 入水声：与画面涟漪对齐
for s in (1.2, 4.0, 6.8, 9.6, 12.4):
    m = int(0.3 * SR); tt = np.arange(m) / SR
    add(np.sin(2 * np.pi * np.cumsum(900 * np.exp(-tt * 18) + 200) / SR) * np.exp(-tt * 14), s, 0.22, rng.uniform(-.4, .4))

# 咖啡段：杯子轻碰
for s in (8.1, 9.3):
    tt = np.arange(int(0.5 * SR)) / SR
    add(sum(a * np.sin(2 * np.pi * f * tt) for f, a in ((2960, 1), (4410, .6), (6230, .35))) * np.exp(-tt * 16), s, 0.05, .3)

st = np.stack([L, Rch], 1)
st *= (np.minimum(1, t / 0.3) * np.minimum(1, (DUR - t) / 1.2))[:, None]
st = np.int16(np.clip(st / np.abs(st).max() * 0.85, -1, 1) * 32767)
OUT = 'sfx.wav' if SFX_ONLY else 'audio.wav'
with wave.open(OUT, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
print(OUT, DUR, 's')
