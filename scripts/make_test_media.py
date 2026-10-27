"""Make a synthetic test clip (a figure moving across a textured background) and a 120 BPM
kick/snare loop, so the whole loop can be tested before real footage is picked.

  python scripts/make_test_media.py   -> tmp/test_clip.mp4, tmp/test_beat.wav
"""
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from beatmask import config  # noqa: E402

OUT = ROOT / "tmp"


def clip(path: Path, seconds=8, fps=30, w=720, h=1280):
    vw = cv2.VideoWriter(str(path.with_suffix(".avi")), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    rng = np.random.default_rng(1)
    bg = (rng.integers(40, 90, (h // 16, w // 16, 3), dtype=np.uint8))
    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_NEAREST)
    for i in range(seconds * fps):
        f = bg.copy()
        cv2.line(f, (0, int(h * 0.8)), (w, int(h * 0.8)), (70, 110, 70), 6)
        cx = int(w * 0.3 + w * 0.4 * (0.5 + 0.5 * np.sin(i / 40)))
        cy = int(h * 0.5)
        cv2.circle(f, (cx, cy - 260), 70, (60, 140, 230), -1)          # head
        cv2.rectangle(f, (cx - 90, cy - 180), (cx + 90, cy + 150), (200, 90, 40), -1)  # body
        cv2.rectangle(f, (cx - 80, cy + 150), (cx - 20, cy + 380), (50, 50, 160), -1)
        cv2.rectangle(f, (cx + 20, cy + 150), (cx + 80, cy + 380), (50, 50, 160), -1)
        vw.write(f)
    vw.release()
    subprocess.run([config.ffmpeg(), "-y", "-loglevel", "error", "-i", str(path.with_suffix(".avi")),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    path.with_suffix(".avi").unlink()


def beat(path: Path, seconds=8, bpm=120, sr=44100):
    import soundfile as sf
    n = seconds * sr
    y = np.zeros(n, np.float32)
    step = 60 / bpm
    t = np.arange(int(0.25 * sr)) / sr
    kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 9)
    noise = np.random.default_rng(0).standard_normal(len(t)).astype(np.float32)
    snare = (noise * np.exp(-t * 22) * 0.5 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 20) * 0.3)
    hat = noise * np.exp(-t * 90) * 0.12
    k = 0
    while k * step < seconds:
        s = int(k * step * sr)
        seg = kick if k % 2 == 0 else snare
        e = min(s + len(seg), n); y[s:e] += seg[: e - s]
        hs = int((k + 0.5) * step * sr)
        if hs < n:
            e = min(hs + len(hat), n); y[hs:e] += hat[: e - hs]
        k += 1
    sf.write(str(path), (y / np.abs(y).max() * 0.9).astype(np.float32), sr)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    clip(OUT / "test_clip.mp4")
    beat(OUT / "test_beat.wav")
    print(f"wrote {OUT/'test_clip.mp4'} and {OUT/'test_beat.wav'}")
