# Build log

## Tue Oct 27 — foundation (Claude, via chat session on the Mac)

**Built**
- `beatmask/` package: ingest (ffmpeg normalize to 1080×1920/30 fps/≤30 s), SAM 3.1 segmenter, offline
  GrabCut fallback, band-flux kick/snare detection, glow/flash/stutter mask-only effects, renderer + export.
- `server.py` + `static/index.html`: 4-step local web app. `scripts/sam_smoke_test.py`, `scripts/make_test_media.py`.
- Docs: README, META-MODELS, SETUP, MUSE-HANDOFF, this log.

**Answered the plan's day-1 open question:** SAM 3.1 video tracking runs on the hosted Meta Model API, and it
accepts point prompts, so "tap the subject" works as designed. No open weights or GPU needed.

**Tested** on synthetic media: kicks/snares exact; all 3 effects render inside the mask only; export is
H.264/AAC 1080×1920; web app runs the whole flow over its API.

**Broke / learned**
- First kick detector caught hi-hats and snare bleed (28 "kicks" in 8 s). Switched to amplitude spectral flux per band + peak picking → exact.
- GrabCut fallback mask spread over the whole frame within a second. Constrained it to a band around the last mask. Still lags fast motion; it's only a fallback.
- Tempo tracker reads the 120 BPM loop as 80.75. Logged as task 4.

**Next:** key in `.env` → smoke test → first real clip through SAM → Wednesday's exported video.

**Speed on Garrick's Intel Mac** (8 s test clip, offline mask): first run 125 s → 87 s after two fixes
(glow halo blurred at quarter resolution; effects computed only in a box around the subject).
First run of the day adds ~2 min of one-time librosa/numba warm-up. A 30 s clip will still take a few
minutes to render — see handoff task 7.

## Tue Oct 27 — tests and first live SAM call (Claude + Muse Code)

**Built**
- Smoke test passed against the live Model API: `sam-3.1` returned a mask (6.5% of frame).
- Muse Code wrote the offline pytest suite on branch `muse/tests` (beats, envelope, segment, mock end to end). Merged to main.

**Broke / fixed**
- Muse's test found `mask_to_frame` crashing when the SAM box lies fully off the frame. Fixed: returns an empty mask.
- On the exFAT external drive, clearing the masks folder raced with macOS `._` files (`FileNotFoundError`). Fixed with `unlink(missing_ok=True)`.

**Next:** real 10-15 s clip through SAM with a tap, then the Odd Wilson track export.
