# Final demo edit — checklist (about 3:00, voiceover)

Do not assemble the final cut until Garrick sends the file names of T2-T6. Raw takes go to
`/Volumes/Garrick Dri/ReelCut AI/reel-studio-build-footage/raw/`. Plan and voiceover lines: `docs/RECORDING-PLAN.md`.

| Take | Content | Source | Status |
|---|---|---|---|
| T1 | Hook: glow result, no talking (0:00-0:10) | `renders/garrick_hallway_glow.mp4` (verified 6/6, signed off by Garrick) | DONE, no recording needed |
| T2 | Intro to camera or voice: who + the problem (~20 s) | Garrick records | NEEDS GARRICK |
| T3 | Live app part 1: load clip + track, tap face, SAM mask appears | screen recording of http://127.0.0.1:8765 | NEEDS GARRICK (file name) |
| T4 | Live app part 2: Glow, Export, "verified 6/6 checks", playback | screen recording, same page | NEEDS GARRICK (re-record the ending after the playback fix `ae7a0ef`) |
| T5 | Verification report + test run (`cat renders/garrick_hallway_glow.mp4.verify.json`, `.venv/bin/python -m pytest -q`) | terminal recording | NEEDS GARRICK |
| T6 | Muse Code: `git log --oneline --grep=Muse`, the task brief, the workshop Agent Console with the signed-off run | terminal + browser recording | NEEDS GARRICK |
| T7 | Flash result + end card | `renders/garrick_hallway_flash.mp4` (verified 6/6, signed off) + end card | DONE, no recording needed |

## When the takes arrive, before the edit (Claude)

- [ ] Each take: length, plays, audio present where expected
- [ ] Frame-check every take for secrets: no key, no `.env`, no Meta dashboard or billing, no private repo
- [ ] Voice tracks through Adobe Enhance Speech
- [ ] Cut the waits in T3/T4 (ingest ~2 min, SAM ~75 s, export + checks ~2.5 min)

## The edit

- [ ] Order T1-T7, total about 3:00
- [ ] Captions for the voiceover lines
- [ ] End card: "Beat Mask, a Reel Studio module" / Meta SAM 3.1 via the Meta Model API / built with Muse Code / Indie Developer Track, Build for Your World / repo link
- [ ] Credit line names Garrick Jordan only
- [ ] Only work built Oct 26 - Nov 4 is shown; no claim of Muse Spark
- [ ] Music only in the final pass (the track is already in T1/T4/T7)
- [ ] Export 1080p H.264 + AAC, then Garrick watches it in full before upload

Draft so far (placeholder, 34 s, no voice): `/Volumes/Garrick Dri/ReelCut AI/reel-studio-build-footage/beat-mask-demo-draft1.mp4`.
