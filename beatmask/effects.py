"""Stage 4 - Effects that touch ONLY the masked subject. Background stays untouched.

Each effect takes the frame (BGR uint8), a soft mask (float32 0..1, feathered) and an
envelope value env in 0..1 (1 on the hit, decaying after). Envelopes come from hit times.
"""
import math

import cv2
import numpy as np

EFFECTS = ("glow", "flash", "stutter")
DEFAULT_DRIVE = {"glow": "kicks", "flash": "snares", "stutter": "beats"}
FLASH_COLORS = [(255, 40, 220), (255, 230, 40), (40, 230, 255)]  # BGR: magenta, cyan, yellow


def envelope(t: float, hits: list[float], decay: float = 0.18, attack: float = 0.0) -> tuple[float, int]:
    """Value of the most recent hit's exponential decay at time t, and that hit's index (-1 if none)."""
    best, idx = 0.0, -1
    for i, h in enumerate(hits):
        if h - attack > t:
            break
        dt = t - h
        v = 1.0 if dt < 0 else math.exp(-dt / decay)
        if v > best:
            best, idx = v, i
    return best, idx


def feather(mask_u8: np.ndarray, px: int = 9) -> np.ndarray:
    m = mask_u8.astype(np.float32) / 255.0
    k = px * 2 + 1
    return cv2.GaussianBlur(m, (k, k), 0)


def _blend(base: np.ndarray, top: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = alpha[..., None]
    return (base.astype(np.float32) * (1 - a) + top.astype(np.float32) * a).clip(0, 255).astype(np.uint8)


def glow(frame, soft, env, **_):
    """Subject brightens and blooms outward on the hit. The halo is blurred at quarter
    resolution (it's a soft glow anyway), which keeps renders fast on a laptop CPU."""
    if env < 0.01:
        return frame
    lifted = cv2.convertScaleAbs(frame, alpha=1.0 + 0.6 * env, beta=40 * env)
    out = _blend(frame, lifted, soft)
    h, w = soft.shape
    q = (w // 4, h // 4)
    s_small = cv2.resize(soft, q, interpolation=cv2.INTER_AREA)
    l_small = cv2.resize(lifted, q, interpolation=cv2.INTER_AREA).astype(np.float32)
    halo_mask = cv2.GaussianBlur(s_small, (0, 0), sigmaX=(18 + 22 * env) / 4)
    halo_src = cv2.GaussianBlur(l_small * s_small[..., None], (0, 0), sigmaX=14 / 4)
    ring = np.clip(halo_mask - s_small, 0, 1)[..., None]
    add = cv2.resize(halo_src * (0.9 * env) * ring * 1.6, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(out.astype(np.float32) + add, 0, 255).astype(np.uint8)


def flash(frame, soft, env, hit_index=0, **_):
    """Subject is washed in a color that cycles each hit."""
    if env < 0.01:
        return frame
    color = np.array(FLASH_COLORS[max(hit_index, 0) % len(FLASH_COLORS)], np.float32)
    tint = frame.astype(np.float32) * 0.35 + color * 0.65
    return _blend(frame, tint.clip(0, 255).astype(np.uint8), soft * (0.85 * env))


def stutter(frame, soft, env, held=None, **_):
    """On the hit the subject freezes (background keeps moving) with an RGB split ghost.

    `held` = (frame, soft) captured on the hit frame; the renderer manages that buffer.
    """
    if held is None or env < 0.05:
        return frame
    hf, hs = held
    out = _blend(frame, hf, hs)
    shift = int(6 + 18 * env)
    b, g, r = cv2.split(hf)
    M1 = np.float32([[1, 0, shift], [0, 1, 0]])
    M2 = np.float32([[1, 0, -shift], [0, 1, 0]])
    h, w = hs.shape
    r_s = cv2.warpAffine(r, M1, (w, h)); b_s = cv2.warpAffine(b, M2, (w, h))
    hs_r = cv2.warpAffine(hs, M1, (w, h)); hs_b = cv2.warpAffine(hs, M2, (w, h))
    ghost = out.astype(np.float32)
    ghost[..., 2] = ghost[..., 2] * (1 - hs_r * 0.6 * env) + r_s * hs_r * 0.6 * env
    ghost[..., 0] = ghost[..., 0] * (1 - hs_b * 0.6 * env) + b_s * hs_b * 0.6 * env
    return ghost.clip(0, 255).astype(np.uint8)


APPLY = {"glow": glow, "flash": flash, "stutter": stutter}
