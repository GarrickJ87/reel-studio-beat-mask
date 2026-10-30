"""Retry smoothing must be able to fix what the verifier objects to: the verifier judges the same
temporally voted masks the renderer draws with (render.temporal_vote), not the raw SAM masks."""
import subprocess

import cv2
import numpy as np

from beatmask import config, render, verify


def test_temporal_vote_fills_a_one_frame_hole_and_is_a_noop_at_zero():
    big = np.zeros((40, 40), np.uint8); big[5:35, 5:35] = 255
    hole = np.zeros_like(big)
    assert render.temporal_vote([], big, 0) is big
    recent = []
    out = [render.temporal_vote(recent, m, 2) for m in (big, big, hole, big)]
    assert (out[2] > 0).sum() == (big > 0).sum(), "the empty frame is outvoted by its neighbours"


def _flicker_case(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run([config.ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"color=c=gray:s={verify.W}x{verify.H}:d=1:r=30", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(clip)], check=True)
    masks = tmp_path / "masks"; masks.mkdir()
    for i in range(30):
        m = np.zeros((verify.H, verify.W), np.uint8)
        if i % 4 == 2:
            m[900:1000, 500:600] = 255        # the subject "shrinks" for one frame: flicker
        else:
            m[400:1600, 200:900] = 255
        cv2.imwrite(str(masks / f"{i:05d}.png"), m)
    return clip, masks


def _flicker_check(results):
    return next(r for r in results if r["name"] == "mask does not flicker or slip")


def test_raw_masks_flicker_but_the_smoothed_masks_pass(tmp_path):
    clip, masks = _flicker_case(tmp_path)
    raw = verify.analyze(clip, clip, masks, [], "glow", smooth=0)
    smoothed = verify.analyze(clip, clip, masks, [], "glow", smooth=2)
    assert _flicker_check(raw)["pass"] is False, _flicker_check(raw)["detail"]
    assert _flicker_check(smoothed)["pass"] is True, _flicker_check(smoothed)["detail"]
