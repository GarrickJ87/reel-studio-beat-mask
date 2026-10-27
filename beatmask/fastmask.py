"""Fast decoder for Meta SAM `one_bit` mask payloads (numba, bit-exact with meta_sam_parser).

meta_sam_parser decodes in pure Python and then re-encodes to check the payload is canonical:
~13 s per mask on this Mac, i.e. an hour for one 8 s clip. The same adaptive binary range coder
compiled with numba takes milliseconds. `install()` swaps it into the official parser, so the
parser's validation of everything except the canonical re-encode still runs.
"""
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(__file__).resolve().parent.parent / ".cache" / "numba"))
from numba import njit  # noqa: E402

_INCREMENT, _COUNT_LIMIT, _CONTEXTS, _PAD = 14, 4096, 1 << 12, 2
_TOP, _BOTTOM, _M32 = 1 << 24, 1 << 16, 0xFFFFFFFF


@njit(cache=True)
def _decode(data, width, height):
    n = data.shape[0]
    pos = 0
    low = np.uint64(0)
    rng = np.uint64(_M32)
    code = np.uint64(0)
    for _ in range(4):
        code = ((code << np.uint64(8)) | np.uint64(data[pos] if pos < n else 0)) & np.uint64(_M32)
        pos += 1
    counts = np.ones(_CONTEXTS * 2, np.int64)
    pw = width + 2 * _PAD
    padded = np.zeros(pw * (height + _PAD), np.uint8)
    out = np.zeros(width * height, np.uint8)
    for y in range(height):
        row = (y + _PAD) * pw + _PAD
        for x in range(width):
            p = row + x
            pr = p - pw
            ea = p - 2 * pw
            ctx = (int(padded[p - 1]) | (int(padded[p - 2]) << 1) | (int(padded[pr - 2]) << 2)
                   | (int(padded[pr - 1]) << 3) | (int(padded[pr]) << 4) | (int(padded[pr + 1]) << 5)
                   | (int(padded[pr + 2]) << 6) | (int(padded[ea - 2]) << 7) | (int(padded[ea - 1]) << 8)
                   | (int(padded[ea]) << 9) | (int(padded[ea + 1]) << 10) | (int(padded[ea + 2]) << 11))
            off = ctx << 1
            zero = counts[off]
            one = counts[off + 1]
            total = zero + one
            scaled = rng // np.uint64(total)
            value = ((code - low) & np.uint64(_M32)) // scaled
            if value >= np.uint64(total):
                value = np.uint64(total - 1)
            if value < np.uint64(zero):
                bit = 0
                cum, freq = np.uint64(0), np.uint64(zero)
            else:
                bit = 1
                cum, freq = np.uint64(zero), np.uint64(one)
            low = (low + scaled * cum) & np.uint64(_M32)
            rng = scaled * freq
            while True:
                if ((low ^ ((low + rng) & np.uint64(_M32))) & np.uint64(_M32)) < np.uint64(_TOP):
                    pass
                elif rng < np.uint64(_BOTTOM):
                    rng = ((np.uint64(_M32) + np.uint64(1) - low) & np.uint64(_M32)) & np.uint64(_BOTTOM - 1)
                else:
                    break
                code = ((code << np.uint64(8)) | np.uint64(data[pos] if pos < n else 0)) & np.uint64(_M32)
                pos += 1
                low = (low << np.uint64(8)) & np.uint64(_M32)
                rng = (rng << np.uint64(8)) & np.uint64(_M32)
            padded[p] = bit
            out[y * width + x] = bit
            counts[off + bit] = (counts[off + bit] + _INCREMENT) & 0xFFFF
            if counts[off] + counts[off + 1] >= _COUNT_LIMIT:
                counts[off] = (counts[off] >> 1) or 1
                counts[off + 1] = (counts[off + 1] >> 1) or 1
    return out


def decode_mask_to_raster(mask) -> bytes:
    """Drop-in for meta_sam_parser.decode_mask_to_raster for one_bit masks (falls back for others)."""
    from meta_sam_parser import _mask_codec as mc
    if mask.encoding != "one_bit" or not isinstance(mask.payload, str) or not mask.payload.startswith("!"):
        return _orig(mask)
    data = np.frombuffer(mc._unpack(mask.payload[1:]), dtype=np.uint8)
    return _decode(data, int(mask.width), int(mask.height)).tobytes()


_orig = None


def install() -> None:
    """Swap the fast decoder into meta_sam_parser (idempotent)."""
    global _orig
    import meta_sam_parser as msp
    from meta_sam_parser import _mask_codec, _segmentation
    if _orig is None:
        _orig = _mask_codec.decode_mask_to_raster
    _segmentation.decode_mask_to_raster = decode_mask_to_raster
    msp.decode_mask_to_raster = decode_mask_to_raster
