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

**Next:** real 10-15 s clip through SAM with a tap, then the Garrick Jordan track export.

## Tue Oct 27 (later) — Step 2: SAM 3.1 tracks a video

**Result:** `scripts/sam_smoke_test.py --video tmp/test_clip.mp4 --tap 540,930` -> subject tracked on 240/240 frames in 71 s; overlay `tmp/sam_smoke_video.png` shows the mask covering the whole synthetic figure, nothing on the background.

**Broke / fixed**
- Meta's `meta_sam_parser` decodes each mask in pure Python and re-encodes it to check it is canonical: ~13 s per mask on this Intel Mac, so ~1 hour for an 8 s clip. Wrote `beatmask/fastmask.py` (numba, same adaptive range coder, verified bit-exact against the reference) and swap it into the parser. ~0.02 s per mask. The canonical re-encode check is skipped; every other parser check still runs.
- exFAT `._*` shadow files were picked up as masks by the smoke test and renderer. Now skipped.
- `pytest` collected `scripts/sam_smoke_test.py`; added `pytest.ini` (`testpaths = tests`).

**Next:** real 10-15 s clip + Garrick Jordan track through the full pipeline (glow, then flash).

## Wed Oct 28 — real clip, tempo fix

**Built**
- Real clip: 6.8 s of Garrick (own footage, 4K 16:9 from a Panasonic, cut and cropped to 1080x1920) in `media/garrick_clip.mp4` (git-ignored).
- SAM 3.1 tapped on the face at frame 0 tracks the whole person (head, shirt, hand) on 206/206 frames in ~40 s; background untouched.
- Full pipeline on that clip + synthetic 120 BPM loop with `glow`: exports 1080x1920 H.264 + AAC in ~2.5 min total on the Intel Mac.
- Tempo fix (task 4): `beats.grid_from_hits` fits a 60-180 BPM grid to the kick+snare hits and replaces the tracker's beats only when the tracker disagrees with the drums. 80.75 -> 120 BPM on the loop; beats land on 0, 0.5, 1.0 s within 30 ms. Kick/snare detection unchanged. Tests in `tests/test_tempo.py`. 14 tests pass.

**Learned**
- Subject is large and moves toward the camera in the start of the file; picked the 26-33 s window where the face and shirt are steady. Frame 0 of the cut is blurred (entering shot) and SAM still finds the person.

**Next:** flash effect on the real clip, mask smoothing if the edge flickers, the real Garrick Jordan track, demo cut.

## Wed Oct 28 (later) — first export with a real Garrick Jordan track

- Track: Garrick Jordan, "Playing in the Hallway" (The Odd-Fi Blueberry Treatment), starting 15 s in; 117 BPM, 8 kicks + 5 snares in the 6.8 s window. Real drumming is looser than the test loop, so the tracker's beat grid is kept (the drum-hit grid is only used when it is clearly steadier).
- Real clip + SAM 3.1 (tap on face, 206/206 frames) + glow on kicks / flash on snares exported at 1080x1920.
- Check vs the original frames: mean change inside the mask is ~49 (glow, on kicks) and ~67 (flash, on snares) on hit frames vs ~4 between hits; the effect peaks 0-1 frames (<= 33 ms) after the hit.
- SAM mask on the Intel Mac: full run (ingest, SAM, glow + flash renders) took ~6 min.

**Next:** watch the exports for mask edge flicker, pick the cut for the demo, record the web app, submission text.

## Wed Oct 28 (evening) — Step 8A: verification layer (Day 3 lesson)

Day 3 (Agents 102): check the work before it ships, inside the step that ships it, so it cannot be skipped. Applied to Beat Mask:
- `beatmask/verify.py`, called from `pipeline.export` (on by default). Layer 1, blocking: 1080x1920 H.264 + audio; subject present on >=90% of frames; background untouched (change outside the dilated mask <= 6 levels on >=95% of sampled frames); every claimed beat shows the effect inside the mask. Layer 2, measured from the frames: subject not lost mid-clip; mask does not flicker or jump. Layer 3: human sign-off, `python -m beatmask.verify signoff EXPORT.mp4` (refuses unless verification passed).
- Failure = export refused with feedback, re-render with stronger temporal mask smoothing (vote over the last 1, then 2 frames); max 3 attempts, then `VerificationEscalation` for a person. No endless loop.
- Real exports: glow 6/6 PASS, flash 6/6 PASS. Negative control: the glow export judged against the snare beats FAILS "effect lands on every claimed beat".
- Stutter: beat check is SKIPPED (honestly reported) because a freeze is only measurable when the subject moves.
- Not done: an LLM-as-judge layer (Muse Spark looking at sampled frames) - possible stretch, would add a Meta model.

## Thu Oct 29 — schedule: color flash + stutter, all 3 effects clean on 3 test clips

**Result: 9/9 exports pass verification on attempt 1.**

| Clip | Glow (kicks) | Flash (snares) | Stutter (beats) |
|---|---|---|---|
| 1, plain wall, 6.8 s (`media/garrick_clip.mp4`) | PASS 8/8 (Oct 28, signed off) | PASS 5/5 (Oct 28, signed off) | PASS 12/12 |
| 2, cap, 12 s (`media/test_clip2_cap.mp4`, new footage) | PASS 13/13 | PASS 10/10 | PASS 29/29 |
| 3, hands, 12 s (`media/test_clip3_hands.mp4`, new footage) | PASS 13/13 | PASS 8/8 | PASS 15/15 |

Tracks: Garrick Jordan, "Playing in the Hallway" (clips 1 and 3) and "Laws of Gravity" (clip 2).

**Built / changed**
- Stutter made readable: 6-frame hold (was 4), wider and stronger color split (14-50 px, was 6-24), and the split now stays inside the subject's outline. Before, it was measurable but hard to see on a still subject, and the wider split leaked onto the background (background check passed at exactly its 95% limit).
- Ahead of Friday's flicker task: verification now judges the same temporally smoothed masks the renderer draws with (`render.temporal_vote`), so a retry with smoothing can actually fix a flicker failure. Test `tests/test_smoothing_verify.py`; 27 tests pass.

**Broke / learned (the verification layer earned its keep)**
- Clip 3 first failed on all three effects, escalated after 3 attempts: "largest centroid jump ~180 px". Cause: the tap was on the face, so SAM tracked only the head, and at frames 60, 107 and 137 it pulled a raised hand into the mask. The glow would have flickered onto a hand for a few frames. Re-tapping on the shirt made SAM track the whole upper body: largest jump 8 px, all three effects pass. The app's tap hint now says to tap the body or shirt, not just the face.

**Next (Fri Oct 30):** timing sync check, render speed; Sat: UI pass + stranger test.

## Fri Oct 30 — schedule: mask edge flicker, timing sync

**Result: effects land on the beat with no visible lag; audio is sample-accurate.** No code change needed.

- Flicker: done Oct 29 (verification judges the same smoothed masks the render uses; retries can fix flicker).
- Audio sync, all 9 verified exports: exported audio cross-correlated against the source track at the chosen start point: **0.0 ms offset, match 1.00** on every export.
- Visual timing, all 9 exports (each hit vs the frame where the effect peaks; stutter vs the frame where the freeze starts, since its difference keeps growing through the hold):

| Clip | Glow (median / max) | Flash (median / max) | Stutter onset (median / max) |
|---|---|---|---|
| 1, plain wall | 8 / 29 ms | 22 / 33 ms | 19 / 51 ms |
| 2, cap | 13 / 27 ms | 25 / 30 ms | 12 / 28 ms |
| 3, hands | 13 / 27 ms | 15 / 32 ms | 19 / 32 ms |

One video frame at 30 fps is 33 ms: a hit that falls between frames shows on the next frame, which is where these numbers come from. Only one stutter hit reached 1.5 frames (51 ms). All are under the ~45 ms where audio-visual offset becomes noticeable.

- Learned: a first pass reported 118-222 ms "lags"; that was the measuring window catching the next hit's pulse on fast tracks (152 BPM), and stutter measured at its peak instead of its onset. Fixed the measurement, not the render. Raw per-frame numbers cached in `tmp/timing_change_cache.npz`.

**Next (Sat Oct 31):** UI pass (simple 4-step flow) + stranger test: clip to export in under 2 minutes, no help.
