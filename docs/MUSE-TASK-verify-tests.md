# Muse Code task 2: offline tests for the export verification layer (branch `muse/verify-tests`)

Read `CLAUDE.md`/`AGENTS.md` first. Work ONLY in this worktree and ONLY add files under `tests/` (plus one table row in `docs/META-MODELS.md`). Do NOT edit anything in `beatmask/`; if a test proves a bug, mark it `xfail(strict=True)` with the reason and report it. Never touch `.env`. No network.
Run tests with: `"/Volumes/Garrick Dri/ReelCut AI/reel-studio-beat-mask/.venv/bin/python" -m pytest tests/test_verify.py -q` (the shared venv; tests must finish in under ~60 s total, so use 1-2 second 1080x1920 synthetic clips made with ffmpeg `lavfi`/numpy, not the 6.8 s real clip).

Module under test: `beatmask/verify.py` (read it first). Write `tests/test_verify.py`:
1. `check_format`: a 1080x1920 H.264 file with audio passes; wrong size fails; no audio fails.
2. `verify_export` on synthetic data (a gray noise "original" clip, a rectangular "subject" mask dir with `00000.png`... PNGs, and an "export" built from the original):
   - export = original with the subject brightened by +80 on the hit frames, background untouched -> passes all checks.
   - export where the BACKGROUND is brightened too -> fails "background untouched".
   - export with no effect at all -> fails "effect lands on every claimed beat".
   - mask dir with no masks -> fails "subject present on enough frames".
   - mask area jumping 3x between frames -> fails "mask does not flicker or slip".
3. `signoff`: refuses when the report says not passed; writes `signoff.approved == true` when passed.
4. `render` with `smooth=2`: a single-frame hole in a mask is filled by the majority vote (test the vote logic through `render.render` on a tiny clip, or replicate and assert the documented behaviour).
Done when: tests committed on this branch, pass (or xfail with reasons), and you add a row for this task to the Muse Code table in `docs/META-MODELS.md`. Hand back a short list: what passed, what xfailed, any bug found.
