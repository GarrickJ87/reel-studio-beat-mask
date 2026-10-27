"""Today's milestone: one successful SAM 3.1 call returns a mask.

  .venv/bin/python scripts/sam_smoke_test.py                  # key check + image test on a test frame
  .venv/bin/python scripts/sam_smoke_test.py --image me.jpg --phrase person
  .venv/bin/python scripts/sam_smoke_test.py --video clip.mp4 --tap 540,900   # tracked video test

Costs (Meta pricing): ~$0.0025 per image, $0.20 per 1,000 video frames (50-frame minimum).
Writes the mask overlay to tmp/sam_smoke_*.png and the raw wire text to tmp/sam_smoke_raw.txt.
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from beatmask import config, media, segment  # noqa: E402

TMP = ROOT / "tmp"


def check_key() -> bool:
    key = config.api_key()
    if not key:
        print("FAIL  no key. Add  MODEL_API_KEY=your_key  to .env (copy .env.example).")
        return False
    r = requests.get(f"{config.BASE_URL}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    if r.status_code != 200:
        print(f"FAIL  key rejected: HTTP {r.status_code} {r.text[:300]}")
        return False
    ids = [m.get("id") for m in r.json().get("data", [])]
    print(f"OK    key works. Models on this account: {', '.join(ids)}")
    if config.SAM_MODEL not in ids:
        print(f"WARN  {config.SAM_MODEL} is not listed for this team - the call below may 404.")
    return True


def overlay(img, full_masks, out):
    vis = img.copy()
    colors = [(255, 60, 200), (60, 230, 255), (80, 255, 120), (255, 200, 40)]
    for i, m in enumerate(full_masks):
        c = np.array(colors[i % len(colors)])
        vis[m > 0] = (vis[m > 0] * 0.4 + c * 0.6).astype(np.uint8)
    cv2.imwrite(str(out), vis)
    return out


def image_test(sam, image: Path, phrase: str | None, tap):
    img = cv2.imread(str(image))
    h, w = img.shape[:2]
    if tap:
        text = sam.point_prompt(tap[0], tap[1], w, h)
        import base64
        part = {"type": "input_image",
                "image_url": "data:image/jpeg;base64," + base64.b64encode(cv2.imencode('.jpg', img)[1]).decode()}
        raw = sam.stream(text, part)
    else:
        raw = sam.segment_image_concept(image, phrase)
    (TMP / "sam_smoke_raw.txt").write_text(raw)
    recs, diag = segment.parse_records(raw)
    if not recs:
        print(f"FAIL? zero masks returned (prompt={'tap ' + str(tap) if tap else repr(phrase)}). "
              "A valid answer if nothing matched - try another phrase or tap.")
        return False
    masks = [segment.mask_to_frame(r, w, h) for r in recs]
    out = overlay(img, masks, TMP / "sam_smoke_image.png")
    cover = [round(float((m > 0).mean()) * 100, 1) for m in masks]
    print(f"OK    SAM 3.1 returned {len(recs)} mask(s); coverage % of frame: {cover}")
    print(f"      overlay -> {out}")
    return True


def video_test(sam, clip: Path, tap):
    work = TMP / "sam_smoke_video"
    norm = work / "clip.mp4"
    info = media.normalize_clip(clip, norm)
    frames = info["frames"]
    print(f"      uploading {frames} frames (~${frames * 0.0002:.3f}) ...")
    res = sam.segment_video(norm, work / "masks", tap[0], tap[1], config.OUT_W, config.OUT_H, frames,
                            raw_path=TMP / "sam_smoke_raw.txt",
                            progress=lambda n, t: print(f"\r      frames streamed: {n}/{t}", end=""))
    print()
    if res.frames_with_mask == 0:
        print("FAIL  no masks came back for the tapped point.")
        return False
    first = media.first_frame(norm, work / "frame0.jpg")
    m0 = sorted(f for f in (work / "masks").glob("*.png") if not f.name.startswith("._"))[0]
    out = overlay(cv2.imread(str(first)), [cv2.imread(str(m0), 0)], TMP / "sam_smoke_video.png")
    print(f"OK    tracked subject on {res.frames_with_mask}/{frames} frames in {res.seconds:.1f}s ({res.detail})")
    print(f"      overlay -> {out}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path)
    ap.add_argument("--phrase", default="person")
    ap.add_argument("--video", type=Path)
    ap.add_argument("--tap", help="x,y in pixels (video: on the 1080x1920 normalized frame)")
    a = ap.parse_args()
    TMP.mkdir(exist_ok=True)
    if not check_key():
        sys.exit(1)
    sam = segment.SamSegmenter()
    tap = tuple(int(v) for v in a.tap.split(",")) if a.tap else None
    try:
        if a.video:
            ok = video_test(sam, a.video, tap or (config.OUT_W // 2, config.OUT_H // 2))
        else:
            image = a.image
            if image is None:  # no image given: use frame 1 of the synthetic test clip
                clip = TMP / "test_clip.mp4"
                if not clip.exists():
                    import subprocess
                    subprocess.run([sys.executable, str(ROOT / "scripts" / "make_test_media.py")], check=True)
                image = media.first_frame(clip, TMP / "sam_smoke_frame.jpg")
                tap = tap or (360, 640)  # the figure's body on the 720x1280 test clip
            ok = image_test(sam, image, a.phrase, tap)
    except segment.SamError as e:
        print(f"FAIL  {e}")
        ok = False
    print("\nMILESTONE MET: SAM 3.1 returned a mask." if ok else "\nNot there yet - see the line above.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
