"""Stage 2 - Segment: the user taps the subject on frame 1; SAM 3.1 returns a mask on every frame.

SamSegmenter  - Meta Model API, model "sam-3.1", point prompt on frame 0, tracked forward.
MockSegmenter - offline fallback (OpenCV GrabCut) so the rest of the loop runs with no key.

Both write one PNG mask per frame to <out_dir>/<frame:05d>.png (0 or 255, full 1080x1920).
A frame with no PNG means "subject not visible" and gets no effect.
"""
import json
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import requests

from . import config


@dataclass
class SegResult:
    frames_with_mask: int
    total_frames: int
    provider: str
    seconds: float
    detail: str = ""


def _empty_dir(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink(missing_ok=True)  # on exFAT, deleting a file also removes its ._ pair
    return d


# ---------------------------------------------------------------- SAM 3.1 (Meta Model API)

class SamError(RuntimeError):
    pass


class SamSegmenter:
    name = "sam-3.1"

    def __init__(self, key: str | None = None, base_url: str = config.BASE_URL,
                 model: str = config.SAM_MODEL, timeout: int = 600):
        self.key = key or config.api_key()
        if not self.key:
            raise SamError("No API key. Put MODEL_API_KEY=... in .env (see .env.example).")
        self.base_url, self.model, self.timeout = base_url, model, timeout

    def _headers(self, json_body=True):
        h = {"Authorization": f"Bearer {self.key}"}
        if json_body:
            h.update({"Content-Type": "application/json", "Accept": "text/event-stream"})
        return h

    @staticmethod
    def _raise(resp):
        if resp.status_code >= 400:
            try:
                err = resp.json().get("error", {})
                msg = f"{err.get('code')}: {err.get('message')}"
            except Exception:
                msg = resp.text[:500]
            raise SamError(f"HTTP {resp.status_code} from Meta Model API - {msg}")

    def upload(self, path: Path) -> str:
        with open(path, "rb") as f:
            r = requests.post(f"{self.base_url}/files", headers=self._headers(False),
                              data={"purpose": "user_data"}, files={"file": (path.name, f)},
                              timeout=self.timeout)
        self._raise(r)
        return r.json()["id"]

    def stream(self, prompt_text: str, media_part: dict, metadata: dict | None = None,
               on_line=None) -> str:
        """POST /v1/responses with stream=true. Returns the full output_text (one line per frame)."""
        body = {"model": self.model,
                "input": [{"type": "message", "role": "user",
                           "content": [{"type": "input_text", "text": prompt_text}, media_part]}],
                "stream": True}
        if metadata:
            body["metadata"] = metadata
        r = requests.post(f"{self.base_url}/responses", headers=self._headers(), json=body,
                          stream=True, timeout=self.timeout)
        self._raise(r)
        chunks = []
        for raw in r.iter_lines(decode_unicode=False):
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace")
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            ev = json.loads(data)
            t = ev.get("type")
            if t == "response.output_text.delta" and ev.get("delta"):
                chunks.append(ev["delta"])
                if on_line:
                    on_line(len(chunks))
            elif t in ("response.failed", "error"):
                raise SamError(f"stream failed: {json.dumps(ev)[:500]}")
        return "".join(chunks)

    # -- prompts
    @staticmethod
    def point_prompt(x: int, y: int, w: int, h: int, obj_id: int = 1,
                     negatives: list[tuple[int, int]] = ()) -> str:
        from meta_sam_parser import FramePrompt, PromptObject, PromptPoint, build_object_prompt
        pts = [PromptPoint(int(x), int(y))] + [PromptPoint(int(a), int(b), "negative") for a, b in negatives]
        return build_object_prompt(size=(w, h), objects=[PromptObject(id=obj_id, prompts=[FramePrompt(frame=0, points=pts)])])

    def segment_video(self, clip: Path, out_dir: Path, x: int, y: int, w: int, h: int,
                      total_frames: int, raw_path: Path | None = None, progress=None) -> SegResult:
        t0 = time.time()
        file_id = self.upload(clip)
        text = self.stream(self.point_prompt(x, y, w, h), {"type": "input_video", "file_id": file_id},
                           metadata={"propagation_direction": "forward", "mask_encoding": "one_bit"},
                           on_line=(lambda n: progress(n, total_frames)) if progress else None)
        if raw_path:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(text)
        n = write_masks(text, out_dir, w, h, keep_object="1")
        return SegResult(n, total_frames, self.name, time.time() - t0, f"file_id={file_id}")

    def segment_image_concept(self, image: Path, phrase: str) -> str:
        import base64
        b64 = base64.b64encode(image.read_bytes()).decode()
        mime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"
        return self.stream(phrase, {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"})


def parse_records(text: str):
    """Parse SAM wire text with Meta's official parser. Returns list of mask records."""
    from meta_sam_parser import CompletedOutcome, video_segmentation_format
    p = video_segmentation_format().create_parser()
    p.push(text, emit=False)
    result = p.finish(CompletedOutcome()).result
    masks = [r for r in result.records if r.kind == "mask"]
    return masks, result.diagnostics


def mask_to_frame(rec, w: int, h: int) -> np.ndarray:
    """Decode a box-local mask and paste it into a full w x h frame."""
    from meta_sam_parser import decode_mask_to_raster
    m = rec.mask
    raster = np.frombuffer(decode_mask_to_raster(m), dtype=np.uint8).reshape(m.height, m.width)
    b = rec.bounds
    left, top = int(round(b.left)), int(round(b.top))
    right, bottom = int(round(b.right)), int(round(b.bottom))
    bw, bh = max(right - left, 1), max(bottom - top, 1)
    local = cv2.resize(raster * 255, (bw, bh), interpolation=cv2.INTER_NEAREST)
    full = np.zeros((h, w), np.uint8)
    x0, y0 = max(left, 0), max(top, 0)
    x1, y1 = min(left + bw, w), min(top + bh, h)
    if x1 <= x0 or y1 <= y0:  # box entirely off the frame: nothing to paste
        return full
    full[y0:y1, x0:x1] = local[y0 - top:y1 - top, x0 - left:x1 - left]
    return full


def write_masks(text: str, out_dir: Path, w: int, h: int, keep_object: str | None = None) -> int:
    _empty_dir(out_dir)
    masks, _diag = parse_records(text)
    per_frame: dict[int, np.ndarray] = {}
    for rec in masks:
        if keep_object is not None and rec.object_id != keep_object:
            continue
        fi = rec.frame.frame_index if rec.frame else 0
        full = mask_to_frame(rec, w, h)
        per_frame[fi] = np.maximum(per_frame[fi], full) if fi in per_frame else full
    for fi, m in per_frame.items():
        cv2.imwrite(str(out_dir / f"{fi:05d}.png"), m)
    return len(per_frame)


# ---------------------------------------------------------------- offline fallback

class MockSegmenter:
    """GrabCut seeded at the tap, re-run every few frames at quarter resolution.

    Rough on purpose: it only exists so ingest/beats/render/export run without a key.
    The demo and submission use SAM 3.1.
    """
    name = "mock-grabcut"

    def __init__(self, every: int = 3, scale: float = 0.25):
        self.every, self.scale = every, scale

    def _grabcut(self, small, seed_mask=None, rect=None):
        mask = np.zeros(small.shape[:2], np.uint8)
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        if seed_mask is not None and seed_mask.any():
            # outside a band around the last mask is definitely background, so it can't spread
            band = cv2.dilate(seed_mask, np.ones((15, 15), np.uint8))
            mask[:] = cv2.GC_BGD
            mask[band > 0] = cv2.GC_PR_BGD
            mask[seed_mask > 0] = cv2.GC_PR_FGD
            core = cv2.erode(seed_mask, np.ones((5, 5), np.uint8))
            mask[core > 0] = cv2.GC_FGD
            cv2.grabCut(small, mask, None, bgd, fgd, 2, cv2.GC_INIT_WITH_MASK)
        else:
            cv2.grabCut(small, mask, rect, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
        return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    def segment_video(self, clip: Path, out_dir: Path, x: int, y: int, w: int, h: int,
                      total_frames: int, raw_path=None, progress=None) -> SegResult:
        t0 = time.time()
        _empty_dir(out_dir)
        cap = cv2.VideoCapture(str(clip))
        s = self.scale
        sw, sh = int(w * s), int(h * s)
        rw, rh = int(sw * 0.42), int(sh * 0.55)
        cx, cy = int(x * s), int(y * s)
        rect = (max(cx - rw // 2, 1), max(cy - rh // 2, 1),
                min(rw, sw - max(cx - rw // 2, 1) - 1), min(rh, sh - max(cy - rh // 2, 1) - 1))
        prev, i, written = None, 0, 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            small = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_AREA)
            if prev is None:
                prev = self._grabcut(small, rect=rect)
                # keep only the blob under the tap
                n, lab = cv2.connectedComponents(prev)
                if n > 1 and lab[min(cy, sh - 1), min(cx, sw - 1)] > 0:
                    prev = np.where(lab == lab[min(cy, sh - 1), min(cx, sw - 1)], 255, 0).astype(np.uint8)
            elif i % self.every == 0 and prev.any() and not prev.all():
                try:
                    nxt = self._grabcut(small, seed_mask=prev)
                    # reject a collapse or an explosion; keep the last good mask
                    if 0.6 < nxt.sum() / max(prev.sum(), 1) < 1.5:
                        prev = nxt
                except cv2.error:
                    pass
            full = cv2.resize(prev, (w, h), interpolation=cv2.INTER_LINEAR)
            full = np.where(full > 127, 255, 0).astype(np.uint8)
            if full.any():
                cv2.imwrite(str(out_dir / f"{i:05d}.png"), full)
                written += 1
            i += 1
            if progress and i % 15 == 0:
                progress(i, total_frames)
        cap.release()
        return SegResult(written, i, self.name, time.time() - t0, "offline fallback, not SAM")


def get_segmenter(kind: str = "auto"):
    if kind == "mock":
        return MockSegmenter()
    if kind == "sam" or (kind == "auto" and config.api_key()):
        return SamSegmenter()
    return MockSegmenter()
