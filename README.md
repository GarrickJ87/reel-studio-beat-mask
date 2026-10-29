# Beat Mask — a Reel Studio module

**Effects that play the person, not the frame.** Load a clip and a track, tap the subject, pick an effect,
and export a vertical video where the effect hits *only the subject*, locked to the kicks and snares.
The background never moves.

Built for the Meta Global AI Developer Hackathon (Indie track, "Build for Your World").

## What was built when (hackathon window: Oct 26 - Nov 4, 2026)

- **Oct 25:** one setup-only commit (project brief, `.gitignore`, `.env.example`, requirements). No app code.
- **Oct 27 onward:** all application code in this repo, written during the event: ingest, SAM 3.1 segmentation client, beat map, the three effects, renderer, web app, tests, docs.
- This is a standalone project. No code from the existing Reel Studio product, including its Meta Vision slot, is copied in.
- The sample clip is the author's own footage; the music is by Odd Wilson (the author).
- Built by Garrick Jordan with Claude Code and Muse Code as assistants under his direction. See `docs/MUSE-LOG.md` for exactly where Meta's models and tools were used.

## How it works

| Stage | What happens | Tech |
|---|---|---|
| 1. Ingest | Clip normalized to 1080×1920, 30 fps, ≤30 s; track decoded | ffmpeg |
| 2. Segment | User taps the subject on frame 1 → **SAM 3.1** segments it and tracks it through every frame | Meta Model API `sam-3.1` (point prompt, forward tracking) |
| 3. Beat map | Kicks (<150 Hz) and snares (1.5–6 kHz) found by band spectral flux; beats by tempo tracking | librosa |
| 4. Render | Glow pulse / color flash / stutter applied inside the feathered mask on each hit | OpenCV |
| 5. Export | H.264 + AAC, 1080×1920, faststart | ffmpeg |

## Run it

```bash
cp .env.example .env            # then paste your Meta Model API key after MODEL_API_KEY=
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python scripts/sam_smoke_test.py      # proves the key + SAM 3.1 work
.venv/bin/python server.py                      # open http://localhost:8765
```

Command line, no UI:

```bash
.venv/bin/python -m beatmask.pipeline --clip my_clip.mov --track odd_wilson.wav --tap 540,900 --effect glow
```

No key yet? Add `--segmenter mock` to run the whole loop with a rough offline mask (OpenCV GrabCut).
It exists only so the rest of the pipeline can be tested; the demo uses SAM 3.1.

## Layout

```
beatmask/   config · media (ingest) · segment (SAM 3.1 + fallback) · beats · effects · render · pipeline
server.py   local web app (standard library only)
static/     the 4-step UI
scripts/    sam_smoke_test.py · make_test_media.py
docs/       BUILD-LOG · META-MODELS · SETUP · MUSE-HANDOFF
```

© 2026 Garrick Jordan (Odd Wilson). Released under the MIT License, see `LICENSE`.
