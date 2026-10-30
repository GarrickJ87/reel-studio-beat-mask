"""Stage 4+5 - Render the effect inside the mask on every hit, mux the track, export 1080x1920 MP4."""
import subprocess
from pathlib import Path

import cv2
import numpy as np

from . import config, effects


def _load_mask(mask_dir: Path, i: int, shape) -> np.ndarray | None:
    p = mask_dir / f"{i:05d}.png"
    if not p.exists():
        return None
    m = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if m is None:
        return None
    if m.shape != shape:
        m = cv2.resize(m, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return m


def temporal_vote(recent: list, m: np.ndarray | None, smooth: int) -> np.ndarray | None:
    """Majority vote of this mask with the previous `smooth` masks (0 = unchanged).

    Shared by the renderer and the export verification, so the checks judge the exact masks
    the effect was drawn with. `recent` is the caller's buffer of past masks.
    """
    if not smooth or m is None:
        return m
    recent.append(m > 0)
    recent[:] = recent[-(smooth + 1):]
    votes = np.sum(recent, axis=0)
    return np.where(votes * 2 > len(recent), 255, 0).astype(np.uint8)


def _bbox(mask: np.ndarray, margin: int, shape) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask)
    h, w = shape
    return (max(int(xs.min()) - margin, 0), max(int(ys.min()) - margin, 0),
            min(int(xs.max()) + margin + 1, w), min(int(ys.max()) + margin + 1, h))


def render(clip: Path, mask_dir: Path, track: Path, hits: list[float], effect: str, out: Path,
           audio_offset: float = 0.0, decay: float | None = None, progress=None, smooth: int = 0) -> Path:
    if effect not in effects.APPLY:
        raise ValueError(f"effect must be one of {effects.EFFECTS}")
    decay = decay or {"glow": 0.22, "flash": 0.16, "stutter": 0.20}[effect]
    hold_frames = 6  # stutter: how many frames the subject stays frozen (0.2 s at 30 fps)
    fn = effects.APPLY[effect]

    cap = cv2.VideoCapture(str(clip))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or config.FPS
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [config.ffmpeg(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
           "-ss", str(audio_offset), "-i", str(track),
           "-map", "0:v", "-map", "1:a", "-t", f"{duration:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    held, held_hit, last_hit = None, -1, -1
    recent = []  # last `smooth` raw masks, for temporal majority smoothing
    i = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = i / fps
            m = _load_mask(mask_dir, i, frame.shape[:2])
            m = temporal_vote(recent, m, smooth)
            env, hit_idx = effects.envelope(t, hits, decay=decay)
            if m is not None and m.any():
                kw = {"hit_index": hit_idx}
                if effect == "stutter":
                    if hit_idx != last_hit and hit_idx >= 0 and env > 0.5:
                        held, held_hit = (frame.copy(), m.copy()), i
                        last_hit = hit_idx
                    if held is not None and i - held_hit < hold_frames:
                        kw["held"] = held
                if env >= 0.01:
                    # work only on the region around the subject (plus room for the glow halo / RGB split)
                    region = m if "held" not in kw else np.maximum(m, kw["held"][1])
                    x0, y0, x1, y1 = _bbox(region, 140, frame.shape[:2])
                    crop = frame[y0:y1, x0:x1]
                    soft = effects.feather(m[y0:y1, x0:x1])
                    if "held" in kw:
                        hf, hm = kw["held"]
                        kw["held"] = (hf[y0:y1, x0:x1], effects.feather(hm[y0:y1, x0:x1]))
                    frame = frame.copy()
                    frame[y0:y1, x0:x1] = fn(crop, soft, env, **kw)
            proc.stdin.write(frame.tobytes())
            i += 1
            if progress and i % 15 == 0:
                progress(i, total)
    finally:
        cap.release()
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace")
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg export failed: {err[-1500:]}")
    return out


def overlay_preview(frame_path: Path, mask_dir: Path, out: Path, frame_index: int = 0) -> Path | None:
    """Frame with the mask tinted on top - shown in the UI after segmentation."""
    frame = cv2.imread(str(frame_path))
    m = _load_mask(mask_dir, frame_index, frame.shape[:2])
    if m is None:
        # first frame the subject appears on
        pngs = sorted(f for f in mask_dir.glob("*.png") if not f.name.startswith("._"))
        if not pngs:
            return None
        m = cv2.imread(str(pngs[0]), cv2.IMREAD_GRAYSCALE)
    tint = frame.copy()
    tint[m > 0] = (tint[m > 0] * 0.4 + np.array([255, 60, 200]) * 0.6).astype(np.uint8)
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(tint, contours, -1, (255, 255, 255), 4)
    cv2.imwrite(str(out), tint)
    return out
