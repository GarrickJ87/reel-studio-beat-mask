# Submission draft — NOT SUBMITTED

Draft for the Cerebral Valley "Submit Project" form, Meta Global AI Developer Hackathon.
Nothing here has been submitted. Garrick gives the final yes and fills the PLACEHOLDER fields.
Hard deadline: Wed Nov 4, 9:00 PM ET / 8:00 PM CT. Freeze Nov 2, target submit Nov 3.

| Field | Value |
|---|---|
| Team name | Reel Studio |
| Contributors | Garrick Jordan (solo) |
| Track | Indie Developer Track |
| Problem statement / theme | Build for Your World |
| Project name | Beat Mask (a Reel Studio module) |
| Public repository | https://github.com/GarrickJ87/reel-studio-beat-mask |
| Demo video (about 3 min, voiceover) | PLACEHOLDER |
| License | MIT (`LICENSE`, copyright Garrick Jordan) |
| Meta models and tools used | SAM 3.1 via the Meta Model API (core); Muse Spark via the Meta Model API (vibe -> effect plan); Muse Code (coding agent: test suites, a review-only pass, and the vibe module) |

## One-liner

Tap a subject once: SAM 3.1 isolates and tracks it, and effects hit only that subject, locked to the kicks and snares, while the background stays untouched.

## Description

Beat-sync tools cut or flash the whole frame. Beat Mask makes the effect play the person instead.

1. Load one short clip and one track.
2. Tap the subject on the first frame. That tap is sent to **SAM 3.1 through the Meta Model API** as a point prompt; SAM segments the subject and tracks it forward through every frame (one hosted call, no GPU or open weights needed).
3. The track is analysed for kicks and snares.
4. Pick an effect: **glow** (the subject brightens and blooms on each kick) or **color flash** (on each snare). The effect is applied only inside the subject's mask.
5. Export a 1080x1920 MP4 with the track.

**The export checks itself before it is handed over** (the Day 3 "verifiable agents" lesson, applied to video): the checks run inside the export step, so they cannot be skipped. Deterministic checks: format, subject present, background untouched, every claimed beat shows the effect inside the mask. Judge-style checks measured from the frames: the mask doesn't flicker or slip, and the subject isn't lost. A failed check re-renders with stronger mask smoothing, at most 3 attempts, then escalates to a person. Nothing is final until a human signs off, and the sign-off is bound to the exact file's hash.

## What was built when (new work only)

- **Oct 25:** one setup-only commit (project brief, `.gitignore`, `.env.example`, requirements). No app code.
- **Oct 27 - Nov 4:** all application code: ingest, the SAM 3.1 client and a fast bit-exact mask decoder, beat map and tempo fix, the effects, renderer and export, the verification layer, the web app, the tests and docs.
- Standalone project. No code from the existing Reel Studio product, and no pre-existing Meta Vision slot, is included or presented.
- The sample clip and the music are Garrick Jordan's own.

## How Meta's tools were used (details: `docs/MUSE-LOG.md`, `docs/META-MODELS.md`)

- **SAM 3.1 (Meta Model API):** subject segmentation and video tracking from a single tap; the core of the app. Real clip tracked on 206/206 frames.
- **Muse Code:** wrote two offline test suites on their own branches (the first found a real crash), and did a review-only pass on the verification layer whose findings hardened it. Also used through Meta's agent workshop (Days 2-3) to build an agent loop and its verification checks.
- Built by Garrick Jordan with Claude Code and Muse Code as assistants under his direction.
- **Muse Spark (Meta Model API):** type a vibe and it picks the effect, the drum that drives it and the intensity (structured JSON output, validated). Built Oct 31 by Muse Code on its own branch, reviewed and wired in by Claude Code; verified live and through a 6/6 export.

## Muse inventory (verified Nov 3, 2026 against git history, files, test runs and live calls)

**Claimed. What it is, what Beat Mask used it for, evidence:**

| Item | What Beat Mask used it for | Evidence |
|---|---|---|
| **Meta Model API** (`api.meta.ai/v1`) | The hosted API every Meta call goes through | Live calls Nov 3: `scripts/sam_smoke_test.py` ("key works", `MILESTONE MET`) and the app's `/api/vibe` |
| **SAM 3.1** via the Meta Model API | Point-prompt segmentation, tracked forward through every frame (`beatmask/segment.py`) | Nov 3 smoke test: 1 mask, 6.5% of frame; real-clip tracking 206/206 and 361/361 frames in `docs/BUILD-LOG.md`; exports verified 6/6 |
| **Muse Spark** (`muse-spark-1.3`, chat completions, strict JSON schema) | Turns a typed vibe into an effect plan (effect, drum, intensity) (`beatmask/vibe.py`) | Commits `d835aeb`, `48d802d`; 7 tests; live call Nov 3 through the app; an export from a Muse Spark plan verified 6/6 on Oct 31 |
| **Muse Code**, test suites | Offline tests on their own branches | `dca2e11` (10 passed, 1 expected failure; found a real crash), `b791162` merged `549c3d3` (11 tests); full suite re-run Nov 3: 34 passed |
| **Muse Code**, vibe module | Wrote `beatmask/vibe.py` and its tests | `d835aeb` on branch `muse/vibe` |
| **Muse Code**, review-only pass | Review of the export verification layer; findings applied on main | `122ff06` (verification always runs, retries fixed at 3, sign-off bound to the export's file hash, every beat must show the effect, stutter measured against the clip's own off-beat change, real frame rate, no-beat and no-consecutive-mask handling, `--out` stays inside the project) |
| **Muse Code**, Meta workshop runs | Built the agent loop and both verification checks in the workshop repo | `run-20261029T004734Z-f97797` (Session 1), `run-20261029T010752Z-538a77` (Session 2, approved by Garrick, status done); logged in `25de9f1` |
| Oct 27 code review of the repo at `be1337c` | Review by Muse (chat assistant), recorded in `docs/MUSE-LOG.md` | Re-checked Nov 3: all Python compiles, no key, no `.env` at that commit |

Evidence files: `docs/MUSE-LOG.md`, `docs/META-MODELS.md` (Muse Code table, 5 rows).

**Workshop context only, not a model in the product:** Days 1-3 of the hackathon workshops (Muse Code, Meta Model API setup, verifiable-agent checks) shaped the export verification layer.

**OPEN, not claimed until recorded:**
- The "$150 free credits in use" state: live calls with the key in `.env` work, but the credit balance and usage were not confirmed for that key. Garrick to confirm in the Meta dashboard.
- Whether the demo video shows Muse use and the app running itself: no candidate video exists yet to check.

**NOT USED, do not claim:** Muse Wonder, Muse Image, Muse Voice Transcribe, Muse Glimmer, Muse Spark Open. (`.env.example` has an unused `MUSE_CODE_MODEL` slot; no product code reads it.) The Fireworks / open-models tryout was a separate workshop experiment and was never run.

## Before submitting (Garrick)

- [x] Team name (Reel Studio) and license (MIT) filled in, confirmed by Garrick
- [ ] Demo video link filled in above
- [ ] Demo video uploaded somewhere judges can open it (for example unlisted YouTube or Vimeo)
- [ ] Final read of README and this text
- [ ] Final yes
