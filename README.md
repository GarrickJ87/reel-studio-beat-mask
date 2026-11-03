# Beat Mask — a Reel Studio module

**Effects that play the person, not the frame.** Load a clip and a track, tap the subject, pick an effect,
and export a vertical video where the effect hits *only the subject*, locked to the kicks and snares.
The background never moves.

Built for the Meta Global AI Developer Hackathon (Indie track, "Build for Your World").

## What was built when (hackathon window: Oct 26 - Nov 4, 2026)

- **Oct 25:** one setup-only commit (project brief, `.gitignore`, `.env.example`, requirements). No app code.
- **Oct 27 onward:** all application code in this repo, written during the event: ingest, SAM 3.1 segmentation client, beat map, the three effects, renderer, web app, tests, docs.
- This is a standalone project. No code from the existing Reel Studio product, including its Meta Vision slot, is copied in.
- The sample clip and the music are the author's own (Garrick Jordan).
- Built by Garrick Jordan with Claude Code and Muse Code as assistants under his direction. See `docs/MUSE-LOG.md` for exactly where Meta's models and tools were used.

## Meta tooling used (checked Nov 3, 2026)

**Used in Beat Mask, with evidence** (details and run IDs: `docs/MUSE-LOG.md`, `docs/META-MODELS.md`):

- **Meta Model API** (`api.meta.ai/v1`): the hosted API the app calls. Live calls re-run on Nov 3 (`scripts/sam_smoke_test.py`, and the app's vibe call).
- **SAM 3.1** (`beatmask/segment.py`): one tap becomes a mask tracked forward through every frame. Nov 3 live call: 1 mask covering 6.5% of the frame (`MILESTONE MET`); real clips tracked on 206/206 and 361/361 frames.
- **Muse Spark** (`beatmask/vibe.py`, model `muse-spark-1.3`): turns a typed vibe into an effect plan (which effect, which drum drives it, how strong), as validated structured JSON. 7 tests; live call re-run Nov 3 through the app.
- **Muse Code**: two offline test suites on their own branches (`dca2e11`, `b791162`), the vibe module (`d835aeb`), a review-only pass whose findings were applied on main (`122ff06`), and the two Meta workshop agent runs (`run-20261029T004734Z-f97797`, `run-20261029T010752Z-538a77`, logged in `25de9f1`).

**Workshop context only (not a model in the product):** the hackathon workshops (Muse Code, Meta Model API setup, verifiable-agent checks) shaped the export verification layer.

**Not used in Beat Mask, not claimed:** Muse Wonder, Muse Image, Muse Voice Transcribe, Muse Glimmer, Muse Spark Open. (`.env.example` has an unused `MUSE_CODE_MODEL` slot; no product code reads it.) The Fireworks / open-models workshop tryout was a separate experiment and was never run.

## How it works

| Stage | What happens | Tech |
|---|---|---|
| 1. Ingest | Clip normalized to 1080×1920, 30 fps, ≤30 s; track decoded | ffmpeg (`beatmask/media.py`) |
| 2. Segment | User taps the subject on frame 1 → **SAM 3.1** segments it and tracks it through every frame; box-local `one_bit` masks decoded by bit-exact numba range decoder | Meta Model API `sam-3.1` + numba (`beatmask/segment.py`, `beatmask/fastmask.py`) |
| 3. Beat map | Kicks (<150 Hz) and snares (1.5–6 kHz) found by band spectral flux; beats by tempo tracking with drum-hit grid correction when the tracker disagrees with steady drums | librosa (`beatmask/beats.py`) |
| 3b. Vibe plan (optional) | User types a text vibe (e.g. `"make it aggressive"`) → **Muse Spark** reads the track summary (tempo, duration, kick/snare/beat counts) and returns a validated JSON plan (`effect`, `drive`, `intensity` in `0..1`, `why`) that pre-selects the UI controls | Meta Model API `muse-spark-1.3`, strict JSON schema (`beatmask/vibe.py`, `POST /api/vibe`) |
| 4. Render | Glow pulse / color flash / stutter applied only inside the feathered subject mask on each hit (`kicks`, `snares`, `beats`, or `onsets`), with intensity scaling (`50–100%`) and optional temporal majority-vote mask smoothing (`temporal_vote`) | OpenCV (`beatmask/effects.py`, `beatmask/render.py`) |
| 5. Export + Verify | Encodes 1080×1920 H.264 (`h264_videotoolbox` on Mac when available, else `libx264`) + AAC (`+faststart`), then automatically runs the 3-layer verification check inside `pipeline.export` before returning | ffmpeg + OpenCV (`beatmask/pipeline.py`, `beatmask/verify.py`) |

### Export verification and human sign-off (`beatmask/verify.py`)

Verification runs inside `pipeline.export` on every export (there is no flag to skip it) and writes `<export>.verify.json`:

- **Layer 1 (deterministic, blocking):**
  - `format 1080x1920 H.264 with audio`: checks `1080×1920` resolution, `h264` video codec, audio stream present, and duration within `0.15 s` of the clip.
  - `subject present on enough frames`: mask present on `≥90%` of frames.
  - `background untouched`: `≥95%` of sampled frames have mean pixel change `≤6.0` outside the dilated subject mask.
  - `effect lands on every claimed beat`: every beat inside the clip must show the effect inside the mask (`glow`/`flash`: peak in-mask change `≥15.0` and `≥3.0×` background change; `stutter`: hit-window change `≥1.5×` median off-beat change).
- **Layer 2 (judge-style, measured from frames on the same `temporal_vote`-smoothed masks used by the renderer):**
  - `subject not lost mid-clip`: longest consecutive gap without a mask is `≤6` frames.
  - `mask does not flicker or slip`: 95th-percentile frame-to-frame relative mask area change `≤12%` and maximum centroid jump `≤90 px`.
- **Bounded retries + escalation:** if any check fails, the export is refused and `pipeline.export` re-renders with stronger temporal majority-vote mask smoothing (`smooth = 0, 1, 2` across at most `3` attempts). If attempt 3 still fails, `VerificationEscalation` is raised to escalate to a person instead of looping.
- **Layer 3 (human sign-off):** verified exports start with `"signoff": "pending"`. Nothing is marked approved until human sign-off via `.venv/bin/python -m beatmask.verify signoff <export.mp4>`, which refuses unless verification passed and confirms the file's SHA-256 hash matches `<export>.verify.json` before writing `"approved": true`.

## Run it

```bash
cp .env.example .env            # then paste your Meta Model API key after MODEL_API_KEY=
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python scripts/sam_smoke_test.py      # proves the key + SAM 3.1 work
.venv/bin/python server.py                      # open http://localhost:8765
```

Command line, no UI:

```bash
.venv/bin/python -m beatmask.pipeline --clip my_clip.mov --track my_track.wav --tap 540,900 --effect glow
.venv/bin/python -m beatmask.verify signoff tmp/work/cli/beatmask_glow_*.mp4
```

No key yet? Add `--segmenter mock` to run the whole loop with a rough offline mask (OpenCV GrabCut).
It exists only so the rest of the pipeline can be tested; the demo uses SAM 3.1.

Offline test suite (no API key or network needed):

```bash
.venv/bin/python -m pytest
```

## Layout

```
beatmask/   config · media (ingest) · segment (SAM 3.1 + fallback) · fastmask · beats · vibe (Muse Spark) · effects · render · verify (3-layer checks + sign-off) · pipeline
server.py   local web app (standard library only: upload, ingest, segment, vibe, export, reset)
static/     the 4-step UI (with optional Muse Spark vibe prompt)
scripts/    sam_smoke_test.py · make_test_media.py · demo_run.sh
tests/      offline pytest suite (beats, tempo, effects, segment, render smoothing, verify, vibe, e2e pipeline)
docs/       BUILD-LOG · META-MODELS · MUSE-LOG · SETUP · MUSE-HANDOFF · SUBMISSION-DRAFT
```

© 2026 Garrick Jordan. Released under the MIT License, see `LICENSE`.
