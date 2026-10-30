"""Step 8A - export verification. Runs INSIDE pipeline.export, so an export cannot skip it.

Layer 1 (deterministic, blocking): format, background untouched, subject present, every claimed
beat effect proven against the beat map, effect confined to the mask.
Layer 2 (judge-style, measured from the frames): the mask neither flickers nor jumps, and the subject
is not lost mid-clip.
Layer 3 (human): nothing is "approved" until Garrick signs off (`python -m beatmask.verify signoff FILE`).

If a check fails the export is refused with feedback; pipeline.export retries (max 3, with stronger
mask smoothing each time) and then escalates to the person instead of looping.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from . import config
from .render import temporal_vote

W, H = config.OUT_W, config.OUT_H
THRESH = {
    "bg_mean_max": 6.0,        # mean |orig - export| outside the (dilated) mask, per frame
    "bg_frames_ok": 0.95,      # fraction of sampled frames under bg_mean_max
    "hit_in_mask_min": 15.0,   # mean change inside the mask on a hit (glow / flash)
    "hit_vs_bg_ratio": 3.0,    # ... and at least this many times the background change
    "hits_proven_min": 1.0,    # every claimed hit must show the effect
    "stutter_visible_ratio": 1.5,  # stutter: change in the hit window vs the median off-beat change
    "mask_frames_min": 0.90,   # fraction of frames with a mask (subject present)
    "max_gap_frames": 6,       # longest run of frames without a mask
    "area_jump_p95": 0.12,     # p95 of relative frame-to-frame mask area change
    "centroid_jump_max": 90.0, # px between consecutive frames
}


def _read(path, every=1, limit=None):
    cap = cv2.VideoCapture(str(path))
    out, i = {}, 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % every == 0:
            out[i] = f
        i += 1
        if limit and i >= limit:
            break
    cap.release()
    return out, i


def _mask(mask_dir: Path, i: int):
    f = Path(mask_dir) / f"{i:05d}.png"
    if not f.exists():
        return None
    m = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
    return None if m is None else (m > 0)


def check_format(export: Path, frames: int) -> dict:
    r = subprocess.run([config.ffprobe(), "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,duration:format=duration",
                        "-of", "json", str(export)], capture_output=True, text=True)
    info = json.loads(r.stdout or "{}").get("streams", [])
    v = next((s for s in info if s.get("codec_type") == "video"), {})
    a = next((s for s in info if s.get("codec_type") == "audio"), None)
    dur = float(v.get("duration") or json.loads(r.stdout or "{}").get("format", {}).get("duration") or 0)
    problems = []
    if (v.get("width"), v.get("height")) != (W, H):
        problems.append(f"size {v.get('width')}x{v.get('height')}, need {W}x{H}")
    if v.get("codec_name") != "h264":
        problems.append(f"video codec {v.get('codec_name')}, need h264")
    if a is None:
        problems.append("no audio track")
    if abs(dur - frames / config.FPS) > 0.15:
        problems.append(f"duration {dur:.2f}s vs clip {frames / config.FPS:.2f}s")
    return {"name": "format 1080x1920 H.264 with audio", "pass": not problems, "detail": "; ".join(problems) or "ok"}


def _stream_stats(orig_path, export_path, mask_dir, sample_every=2, smooth=0):
    """Walk both videos in lockstep at quarter resolution; keep only per-frame numbers (no frames in memory)."""
    co, ce = cv2.VideoCapture(str(orig_path)), cv2.VideoCapture(str(export_path))
    fps = co.get(cv2.CAP_PROP_FPS) or config.FPS
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    hw = (W // 4, H // 4)  # quarter resolution is plenty for change statistics
    st = {"fps": fps, "n": 0, "have": [], "area": [], "centroid": [], "in_change": {}, "bg_change": []}
    i, recent = 0, []
    while True:
        ok1, fo = co.read(); ok2, fe = ce.read()
        if not (ok1 and ok2):
            break
        m = _mask(mask_dir, i)
        if smooth and m is not None:  # judge the same voted masks the render drew with
            m = temporal_vote(recent, m.astype(np.uint8) * 255, smooth) > 0
        m = None if m is None else cv2.resize(m.astype(np.uint8), hw, interpolation=cv2.INTER_NEAREST) > 0
        present = m is not None and bool(m.any())
        st["have"].append(present)
        st["area"].append(float(m.sum()) * 16 if present else 0.0)
        st["centroid"].append(np.array(np.nonzero(m)).mean(axis=1) * 4 if present else None)
        if present:
            a = cv2.resize(fo, hw, interpolation=cv2.INTER_AREA).astype(np.float32)
            b = cv2.resize(fe, hw, interpolation=cv2.INTER_AREA).astype(np.float32)
            d = np.abs(a - b).mean(axis=2)
            st["in_change"][i] = float(d[m].mean())
            if i % sample_every == 0:
                ring = cv2.dilate(m.astype(np.uint8), kernel) > 0
                st["bg_change"].append(float(d[~ring].mean()) if (~ring).any() else 0.0)
        i += 1
    co.release(); ce.release()
    st["n"] = i
    return st


def analyze(orig_path, export_path, mask_dir, hits, effect, smooth=0) -> list[dict]:
    """Return the list of check results (each {name, layer, pass|skip, detail})."""
    st = _stream_stats(orig_path, export_path, mask_dir, smooth=smooth)
    fps = st["fps"]
    n, have, in_vals, bg_vals = st["n"], st["have"], st["in_change"], st["bg_change"]
    results = []
    masks_area, centroids = st["area"], st["centroid"]
    # --- layer 1: deterministic ---
    frac = sum(have) / max(n, 1)
    results.append({"name": "subject present on enough frames", "layer": 1, "pass": frac >= THRESH["mask_frames_min"],
                    "detail": f"mask on {sum(have)}/{n} frames ({frac:.0%}), need {THRESH['mask_frames_min']:.0%}"})
    bg_frac = sum(v <= THRESH["bg_mean_max"] for v in bg_vals) / max(len(bg_vals), 1)
    results.append({"name": "background untouched", "layer": 1, "pass": bg_frac >= THRESH["bg_frames_ok"],
                    "detail": f"{bg_frac:.0%} of sampled frames have background change <= {THRESH['bg_mean_max']} "
                              f"(mean {np.mean(bg_vals) if bg_vals else 0:.1f})"})

    bg_mean = max(float(np.mean(bg_vals)) if bg_vals else 0.0, 0.5)
    in_clip = [t for t in hits if int(round(t * fps)) < n - 1]
    if not in_clip:
        results.append({"name": "effect lands on every claimed beat", "layer": 1, "pass": None,
                        "detail": "skipped: no beats inside the clip"})
    elif effect == "stutter":
        # The freeze only differs from the original when the subject moves, so judge it against the
        # clip's own off-beat change: a stutter that changes nothing visible must not pass.
        near = set()
        for t in in_clip:
            near.update(range(int(round(t * fps)), int(round(t * fps)) + 5))
        off = [v for i, v in in_vals.items() if i not in near]
        base = max(float(np.median(off)) if off else 0.0, 0.5)
        weak = []
        for t in in_clip:
            f0 = int(round(t * fps))
            window = [in_vals[j] for j in range(f0, min(f0 + 5, n)) if j in in_vals]
            if not window or max(window) < THRESH["stutter_visible_ratio"] * base:
                weak.append(round(t, 2))
        ok = not weak
        results.append({"name": "effect lands on every claimed beat", "layer": 1, "pass": ok,
                        "detail": f"stutter visible on {len(in_clip) - len(weak)}/{len(in_clip)} beats "
                                  f"(needs {THRESH['stutter_visible_ratio']}x the off-beat change)"
                                  + (f"; not visible at {weak}" if weak else "")})
    else:
        unproven = []
        for t in in_clip:
            f0 = int(round(t * fps))
            window = [in_vals[j] for j in range(f0, min(f0 + 4, n)) if j in in_vals]
            peak = max(window) if window else 0.0
            if not window or peak < THRESH["hit_in_mask_min"] or peak < THRESH["hit_vs_bg_ratio"] * bg_mean:
                unproven.append(round(t, 2))
        proven = (len(in_clip) - len(unproven)) / len(in_clip)
        results.append({"name": "effect lands on every claimed beat", "layer": 1,
                        "pass": proven >= THRESH["hits_proven_min"],
                        "detail": f"{len(in_clip) - len(unproven)}/{len(in_clip)} beats show the effect inside the mask"
                                  + (f"; unproven at {unproven}" if unproven else "")})

    # --- layer 2: judge-style ---
    gap, longest = 0, 0
    for h in have:
        gap = 0 if h else gap + 1
        longest = max(longest, gap)
    results.append({"name": "subject not lost mid-clip", "layer": 2, "pass": longest <= THRESH["max_gap_frames"],
                    "detail": f"longest gap {longest} frames (max {THRESH['max_gap_frames']})"})
    idx = [i for i in range(1, n) if have[i] and have[i - 1]]
    if idx:
        rel = np.array([abs(masks_area[i] - masks_area[i - 1]) / max(masks_area[i - 1], 1) for i in idx])
        cen = [float(np.hypot(*(centroids[i] - centroids[i - 1]))) for i in idx]
        p95, cmax = float(np.percentile(rel, 95)), max(cen)
        results.append({"name": "mask does not flicker or slip", "layer": 2,
                        "pass": p95 <= THRESH["area_jump_p95"] and cmax <= THRESH["centroid_jump_max"],
                        "detail": f"area change p95 {p95:.1%} (max {THRESH['area_jump_p95']:.0%}), "
                                  f"largest centroid jump {cmax:.0f}px (max {THRESH['centroid_jump_max']:.0f})"})
    else:
        results.append({"name": "mask does not flicker or slip", "layer": 2, "pass": None,
                        "detail": "skipped: no two consecutive masks to compare"})
    return results


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_export(clip, export, mask_dir, hits, effect, smooth: int = 0) -> dict:
    t0 = time.time()
    _, frames = _read(clip, every=10 ** 9)
    results = [{**check_format(Path(export), frames), "layer": 1}] + analyze(clip, export, mask_dir, hits, effect, smooth=smooth)
    failed = [r for r in results if r["pass"] is False]
    return {"export": str(export), "sha256": _sha256(export), "effect": effect, "checked_seconds": round(time.time() - t0, 1),
            "passed": not failed, "failed": [r["name"] for r in failed], "checks": results,
            "signoff": "pending"}


def feedback(report: dict) -> str:
    lines = [f"- {r['name']}: {r['detail']}" for r in report["checks"] if r["pass"] is False]
    return "Export refused:\n" + "\n".join(lines)


def print_report(report: dict, file=sys.stdout):
    for r in report["checks"]:
        tag = "PASS" if r["pass"] else ("SKIP" if r["pass"] is None else "FAIL")
        print(f"  [{tag}] L{r.get('layer', 1)} {r['name']}: {r['detail']}", file=file)


class VerificationEscalation(RuntimeError):
    """Raised after the last retry: a person must look at the export."""
    def __init__(self, report):
        super().__init__("verification failed after retries; escalate to Garrick\n" + feedback(report))
        self.report = report


def signoff(export: Path, who: str = "Garrick Jordan") -> Path:
    rep = Path(str(export) + ".verify.json")
    if not rep.exists():
        raise SystemExit(f"no verification report for {export}; export it through beatmask.pipeline first")
    data = json.loads(rep.read_text())
    if not data.get("passed"):
        raise SystemExit("verification did not pass; cannot sign off. Fix the export first.")
    if data.get("sha256") and data["sha256"] != _sha256(export):
        raise SystemExit("this file changed after it was verified; re-export it so it is verified again")
    data["signoff"] = {"by": who, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "approved": True}
    rep.write_text(json.dumps(data, indent=1))
    return rep


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "signoff":
        print("signed off:", signoff(Path(sys.argv[2])))
    else:
        print("usage: python -m beatmask.verify signoff EXPORT.mp4")
