"""Paper-wipe transition asset: a torn cream sheet slides left to right across the frame, stepped at 12fps (stop-motion).
Output: overlays/paper_wipe_16f.mov (ProRes 4444 with alpha). The cut under it should land on frame 8 of the clip.
usage: python3 fx.py"""
import numpy as np, subprocess, os
from PIL import Image, ImageFilter
W, H, N, P = 1080, 1920, 16, 1800            # frame size, wipe frames, paper width
rng = np.random.default_rng(11)
os.makedirs("overlays/wipe", exist_ok=True)

def paper_strip():
    h = H + 200
    base = np.zeros((h, P, 3), np.float32); base[:] = (241, 233, 214)
    L = lambda a, s: np.array(Image.fromarray(np.clip(128 + a, 0, 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(s))).astype(np.float32) - 128
    fib = L(rng.normal(0, 22, (h, P)), 1.1)
    base += fib[..., None] * 0.55
    blot = np.array(Image.fromarray(np.clip(128 + rng.normal(0, 40, (h // 24, P // 24)), 0, 255).astype(np.uint8), "L").resize((P, h), Image.BICUBIC)).astype(np.float32) - 128
    base += blot[..., None] * 0.12
    rgb = np.clip(base, 0, 255).astype(np.uint8)
    # torn left and right edges (random walk), plus a lighter fibre rim
    def edge(h):
        e = np.cumsum(rng.normal(0, 3.2, h)); e -= np.linspace(e[0], e[-1], h); return np.clip(e, -26, 26)
    el, er = edge(h), edge(h)
    alpha = np.zeros((h, P), np.uint8); rim = np.zeros((h, P), np.float32)
    for y in range(h):
        a, b = int(42 + el[y]), int(P - 42 + er[y]); alpha[y, a:b] = 255
        rim[y, a:a + 7] = 1; rim[y, b - 7:b] = 1
    rgb = (rgb * (1 - rim[..., None] * 0.25) + 255 * rim[..., None] * 0.25).astype(np.uint8)
    im = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
    sh = Image.new("RGBA", im.size, (40, 28, 14, 0)); sh.putalpha(im.split()[3].point(lambda v: int(v * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    out = Image.new("RGBA", (P + 60, h + 40), (0, 0, 0, 0)); out.alpha_composite(sh, (24, 24)); out.alpha_composite(im, (0, 0))
    return out

strip = paper_strip()
ease = lambda u: 0.5 - 0.5 * np.cos(np.pi * u)
for f in range(N):
    u = ease(min(f // 2 * 2, N - 1) / (N - 1))                     # step every 2 frames = 12fps cadence
    left = int(-P + u * (W + P))                                    # left edge: -P (just off left) -> W (just off right)
    cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cv.alpha_composite(strip, (left, -100 - 20)) if False else cv.paste(strip, (left, -110), strip)
    cv.save(f"overlays/wipe/w_{f:02d}.png")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", "overlays/wipe/w_%02d.png", "-c:v", "prores_ks", "-profile:v", "4444",
                "-pix_fmt", "yuva444p10le", "overlays/paper_wipe_16f.mov"], check=True)
print("ok overlays/paper_wipe_16f.mov")
