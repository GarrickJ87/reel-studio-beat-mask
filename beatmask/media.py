"""Stage 1 - Ingest: normalize any clip to 1080x1920 / 30 fps / H.264 / faststart, <=30 s.

Everything downstream (SAM coordinates, masks, render) works in this one pixel space,
so a tap on the preview maps straight onto what SAM 3.1 sees.
"""
import json
import subprocess
from pathlib import Path

import cv2

from . import config


def run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd[:3])}...\n{res.stderr[-1500:]}")
    return res.stdout


def probe(path: Path) -> dict:
    out = run([config.ffprobe(), "-v", "error", "-print_format", "json",
               "-show_streams", "-show_format", str(path)])
    data = json.loads(out)
    v = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    info = {"duration": float(data["format"].get("duration", 0) or 0), "has_audio": a is not None}
    if v:
        num, _, den = v.get("avg_frame_rate", "0/1").partition("/")
        info.update(width=int(v["width"]), height=int(v["height"]),
                    fps=float(num) / float(den or 1) if float(den or 1) else 0.0,
                    frames=int(v.get("nb_frames", 0) or 0))
    return info


def normalize_clip(src: Path, dst: Path, start: float = 0.0) -> dict:
    """Center-crop to 9:16, scale to 1080x1920, 30 fps, max 30 s, no audio (the track replaces it)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    w, h = config.OUT_W, config.OUT_H
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
          f"crop={w}:{h},fps={config.FPS},setsar=1")
    run([config.ffmpeg(), "-y", "-ss", str(start), "-i", str(src), "-t", str(config.MAX_SECONDS),
         "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)])
    info = probe(dst)
    info["frames"] = count_frames(dst)
    return info


def count_frames(path: Path) -> int:
    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return n


def first_frame(clip: Path, dst: Path) -> Path:
    cap = cv2.VideoCapture(str(clip))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"could not read a frame from {clip}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), frame)
    return dst


def extract_audio(src: Path, dst: Path) -> Path:
    """Decode the track to 44.1 kHz mono WAV for beat analysis."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    run([config.ffmpeg(), "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "44100", str(dst)])
    return dst
