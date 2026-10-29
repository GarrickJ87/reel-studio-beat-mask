"""Offline tests for the export verification layer (beatmask/verify.py).

Synthetic only: 1 s 1080x1920 clips built from numpy frames piped to ffmpeg
(libx264 + aac), or straight ffmpeg lavfi sources. No network, no API key,
no real footage. Only this file is added; nothing in beatmask/ is touched.
"""
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import cv2
import numpy as np
import pytest

from beatmask import config, render, verify

W, H, FPS = config.OUT_W, config.OUT_H, config.FPS
N_FRAMES = 30  # 1 s at 30 fps
HITS = [0.2, 0.5, 0.8]  # -> frames 6, 15, 24
RECT = (440, 860, 640, 1160)  # x0, y0, x1, y1: the synthetic "subject"
ROOT = Path(__file__).resolve().parent.parent
SYNTH = ROOT / "tmp" / "verify-synth"


def _probe_cv2_h264():
    """True when stock cv2.VideoCapture can open an H.264 MP4 in this env."""
    import cv2 as _cv
    probe = Path(tempfile.gettempdir()) / "cv2_h264_probe.mp4"
    try:
        vw = _cv.VideoWriter(str(probe), _cv.VideoWriter_fourcc(*"mp4v"), 30, (64, 48))
        vw.write(np.zeros((48, 64, 3), np.uint8))
        vw.release()
        cap = _cv.VideoCapture(str(probe))
        ok = cap.isOpened()
        cap.release()
        return ok
    except Exception:
        return False
    finally:
        probe.unlink(missing_ok=True)


_CV2_READS_H264 = _probe_cv2_h264()

if not _CV2_READS_H264:
    from collections import OrderedDict

    # Eager full-video cache (LRU, 3 entries): one verify_export opens the
    # same file 3 times, and every scenario re-reads the shared clip.
    # Without this the suite decodes the same bytes ~15 times (>60 s total).
    _FRAME_CACHE: "OrderedDict[str, tuple]" = OrderedDict()

    class _PipeCapture:
        """Test-only cv2.VideoCapture replacement: decode via the ffmpeg CLI.

        This venv's OpenCV ships without its ffmpeg videoio plugin, so stock
        VideoCapture cannot open H.264 MP4s here (verified by probe above).
        Production code is untouched; frames are still decoded from the real
        exported bytes, just through a different reader.
        """

        def __init__(self, path, *args):
            key = str(path)
            hit = _FRAME_CACHE.get(key)
            if hit is None:
                info = json.loads(subprocess.run(
                    [config.ffprobe(), "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,duration",
                     "-of", "json", key],
                    capture_output=True, text=True, check=True).stdout)["streams"][0]
                num, _, den = info.get("avg_frame_rate", "30/1").partition("/")
                w, h = int(info["width"]), int(info["height"])
                fps = float(num) / float(den or 1)
                nb = int(info.get("nb_frames") or 0)
                n = nb or round(float(info.get("duration", 0)) * fps)
                raw = subprocess.run(
                    [config.ffmpeg(), "-v", "error", "-i", key,
                     "-pix_fmt", "bgr24", "-f", "rawvideo", "-"],
                    check=True, capture_output=True).stdout
                frames = [np.frombuffer(raw[i:i + w * h * 3], np.uint8)
                          .reshape(h, w, 3).copy()
                          for i in range(0, len(raw), w * h * 3)
                          if len(raw[i:i + w * h * 3]) == w * h * 3]
                hit = (w, h, fps, frames)
                _FRAME_CACHE[key] = hit
                while len(_FRAME_CACHE) > 3:
                    _FRAME_CACHE.popitem(last=False)
            else:
                _FRAME_CACHE.move_to_end(key)
            self._w, self._h, self._fps, self._frames = hit
            self._n = len(self._frames)
            self._i, self._open = 0, True

        def isOpened(self):
            return self._open

        def read(self):
            if self._i >= self._n:
                return False, None
            f = self._frames[self._i]
            self._i += 1
            return True, f

        def get(self, prop):
            return {cv2.CAP_PROP_FRAME_WIDTH: float(self._w),
                    cv2.CAP_PROP_FRAME_HEIGHT: float(self._h),
                    cv2.CAP_PROP_FPS: float(self._fps),
                    cv2.CAP_PROP_FRAME_COUNT: float(self._n)}.get(prop, 0.0)

        def release(self):
            self._open = False


    cv2.VideoCapture = _PipeCapture


def _ffmpeg(*args):
    subprocess.run([config.ffmpeg(), "-y", "-loglevel", "error", *args], check=True)


def _encode(frames, path, audio=True):
    """H.264 (+AAC sine) MP4 from BGR numpy frames."""
    h, w = frames[0].shape[:2]
    dur = len(frames) / FPS
    cmd = ["-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
           "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}:sample_rate=44100"]
    cmd += ["-map", "0:v"] + (["-map", "1:a"] if audio else [])
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
            "-pix_fmt", "yuv420p"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    cmd += ["-movflags", "+faststart", "-shortest", str(path)]
    p = subprocess.Popen([config.ffmpeg(), "-y", "-loglevel", "error", *cmd],
                         stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.ascontiguousarray(f).tobytes())
    p.stdin.close()
    assert p.wait() == 0, f"ffmpeg encode failed for {path}"


def _base_frames(seed=7):
    rng = np.random.default_rng(seed)
    noise = rng.integers(-4, 5, (N_FRAMES, H, W, 3), dtype=np.int16)
    return np.clip(128 + noise, 0, 255).astype(np.uint8)


def _brighten(frames, idx, rect=None):
    out = [f.copy() for f in frames]
    for i in idx:
        if rect is None:
            out[i] = np.clip(out[i].astype(np.int16) + 80, 0, 255).astype(np.uint8)
        else:
            x0, y0, x1, y1 = rect
            out[i][y0:y1, x0:x1] = np.clip(
                out[i][y0:y1, x0:x1].astype(np.int16) + 80, 0, 255).astype(np.uint8)
    return out


def _hit_frames():
    return [int(round(t * FPS)) for t in HITS]


def _write_mask(path, rect=None):
    m = np.zeros((H, W), np.uint8)
    if rect is not None:
        x0, y0, x1, y1 = rect
        m[y0:y1, x0:x1] = 255
    cv2.imwrite(str(path), m)


@pytest.fixture(scope="module")
def synth():
    """Original clip + steady rectangular mask dir, shared by the verify cases."""
    SYNTH.mkdir(parents=True, exist_ok=True)
    clip = SYNTH / "orig.mp4"
    mask_dir = SYNTH / "masks"
    mask_dir.mkdir(exist_ok=True)
    if not clip.exists():
        _encode(_base_frames(), clip)
    if not (mask_dir / "00000.png").exists():
        for i in range(N_FRAMES):
            _write_mask(mask_dir / f"{i:05d}.png", RECT)
    return {"clip": clip, "masks": mask_dir, "base": _base_frames()}


def _export_of(synth, name, frames):
    out = SYNTH / name
    if not out.exists():
        _encode(frames, out)
    return out


def _failed(report):
    return report["failed"]


# --- 1. check_format ---

def test_check_format_passes(tmp_path):
    good = tmp_path / "good.mp4"
    _ffmpeg("-f", "lavfi", "-i", f"testsrc2=s={W}x{H}:d=1:r={FPS}",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1:sample_rate=44100",
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(good))
    r = verify.check_format(good, N_FRAMES)
    assert r["pass"] is True, r
    assert r["name"] == "format 1080x1920 H.264 with audio"


def test_check_format_wrong_size_fails(tmp_path):
    small = tmp_path / "small.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=s=640x480:d=1:r=30",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1:sample_rate=44100",
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(small))
    r = verify.check_format(small, N_FRAMES)
    assert r["pass"] is False, r
    assert "size" in r["detail"] and "640x480" in r["detail"], r


def test_check_format_no_audio_fails(tmp_path):
    mute = tmp_path / "mute.mp4"
    _ffmpeg("-f", "lavfi", "-i", f"testsrc2=s={W}x{H}:d=1:r={FPS}",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(mute))
    r = verify.check_format(mute, N_FRAMES)
    assert r["pass"] is False, r
    assert "no audio" in r["detail"], r


# --- 2. verify_export on synthetic data ---

def test_verify_export_passes_all_checks(synth):
    export = _export_of(synth, "export_pass.mp4",
                        _brighten(synth["base"], _hit_frames(), RECT))
    rep = verify.verify_export(synth["clip"], export, synth["masks"], HITS, "glow")
    assert rep["passed"] is True, rep
    assert rep["failed"] == [], rep


def test_verify_export_background_change_fails(synth):
    export = _export_of(synth, "export_bg.mp4",
                        _brighten(synth["base"], _hit_frames(), rect=None))
    rep = verify.verify_export(synth["clip"], export, synth["masks"], HITS, "glow")
    assert rep["passed"] is False, rep
    assert "background untouched" in _failed(rep), rep


def test_verify_export_no_effect_fails(synth):
    export = _export_of(synth, "export_none.mp4", synth["base"])
    rep = verify.verify_export(synth["clip"], export, synth["masks"], HITS, "glow")
    assert rep["passed"] is False, rep
    assert "effect lands on every claimed beat" in _failed(rep), rep


def test_verify_export_no_masks_fails(synth, tmp_path):
    empty = tmp_path / "empty_masks"
    empty.mkdir()
    export = _export_of(synth, "export_pass.mp4",
                        _brighten(synth["base"], _hit_frames(), RECT))
    rep = verify.verify_export(synth["clip"], export, empty, HITS, "glow")
    assert rep["passed"] is False, rep
    assert "subject present on enough frames" in _failed(rep), rep


def test_verify_export_flickering_mask_fails(synth, tmp_path):
    flick = tmp_path / "flick_masks"
    flick.mkdir()
    x0, y0, x1, y1 = RECT
    cx = (x0 + x1) // 2
    for i in range(N_FRAMES):
        # same centre, but area jumps 3x frame to frame (200px <-> 600px wide)
        w = 200 if i % 2 == 0 else 600
        m = np.zeros((H, W), np.uint8)
        m[y0:y1, cx - w // 2:cx + w // 2] = 255
        cv2.imwrite(str(flick / f"{i:05d}.png"), m)
    export = _export_of(synth, "export_pass.mp4",
                        _brighten(synth["base"], _hit_frames(), RECT))
    rep = verify.verify_export(synth["clip"], export, flick, HITS, "glow")
    assert rep["passed"] is False, rep
    assert "mask does not flicker or slip" in _failed(rep), rep


# --- 3. signoff ---

def test_signoff_refuses_unpassed_report(tmp_path):
    export = tmp_path / "export.mp4"
    export.touch()
    (tmp_path / "export.mp4.verify.json").write_text(json.dumps({"passed": False}))
    with pytest.raises(SystemExit):
        verify.signoff(export)


def test_signoff_approves_passed_report(tmp_path):
    export = tmp_path / "export.mp4"
    export.touch()
    (tmp_path / "export.mp4.verify.json").write_text(json.dumps({"passed": True}))
    rep = verify.signoff(export)
    assert json.loads(rep.read_text())["signoff"]["approved"] is True


# --- 4. render smooth=2 fills a single-frame hole ---

def test_render_smooth_fills_single_frame_hole(tmp_path):
    w2, h2, n = 96, 64, 5
    hole = 2
    rect = (30, 20, 66, 44)
    rng = np.random.default_rng(3)
    frames = [np.clip(110 + rng.integers(-2, 3, (h2, w2, 3),
                                        dtype=np.int16), 0, 255).astype(np.uint8)
              for _ in range(n)]
    clip = tmp_path / "tiny.mp4"
    # tiny encode without audio (render muxes the track itself)
    h0, w0 = frames[0].shape[:2]
    p = subprocess.Popen(
        [config.ffmpeg(), "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w0}x{h0}",
         "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         "-pix_fmt", "yuv420p", str(clip)], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.ascontiguousarray(f).tobytes())
    p.stdin.close()
    assert p.wait() == 0

    masks = tmp_path / "masks"
    masks.mkdir()
    for i in range(n):
        m = np.zeros((h2, w2), np.uint8)
        if i != hole:  # frame 2 exists but is empty: the "hole"
            m[rect[1]:rect[3], rect[0]:rect[2]] = 255
        cv2.imwrite(str(masks / f"{i:05d}.png"), m)

    track = tmp_path / "silence.wav"
    with wave.open(str(track), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00" * 2 * 44100)  # 1 s, longer than the 5-frame clip

    hits = [hole / FPS]
    out_plain = render.render(clip, masks, track, hits, "glow", tmp_path / "plain.mp4")
    out_smooth = render.render(clip, masks, track, hits, "glow",
                               tmp_path / "smooth.mp4", smooth=2)

    def rect_mean(path, idx):
        cap = cv2.VideoCapture(str(path))
        for _ in range(idx + 1):
            ok, f = cap.read()
            assert ok
        cap.release()
        return f[rect[1]:rect[3], rect[0]:rect[2]].mean()

    orig = np.asarray(frames[hole][rect[1]:rect[3], rect[0]:rect[2]]).mean()
    assert rect_mean(out_smooth, hole) - orig > 15, "smoothed mask should take the effect"
    assert rect_mean(out_plain, hole) - orig < 5, "raw hole should stay untouched"
