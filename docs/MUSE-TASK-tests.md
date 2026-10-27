# Muse Code task: offline pytest tests (branch `muse/tests`)

Read CLAUDE.md first. Work ONLY on this branch. Do not touch main, `.env`, or app code unless a test proves a bug (report it instead of fixing).
Write tests in `tests/`, no network. Run with `.venv/bin/python -m pytest`.

1. `beats.analyze` on `tmp/test_beat.wav` (make it with `scripts/make_test_media.py` if missing): 8 kicks within +-30 ms of 0,1,2...7 s; 8 snares at 0.5,1.5...7.5 s.
2. `effects.envelope`: 1.0 at a hit, decays after, most recent hit wins, -1 index before the first hit.
3. `segment.mask_to_frame`: a box running off the frame edge is clipped, not crashed.
4. `segment.parse_records` on the sample line in `docs/META-MODELS.md`: 2 records, ids "0" and "1".
5. `pipeline` end to end with `--segmenter mock` on the synthetic media: MP4 exists, is 1080x1920, has audio.

Done when: tests pass (or failures are listed with the exact assertion), committed on `muse/tests`.
Hand back a short list of results. Claude Code reviews and merges to main.
After finishing, add a row to the Muse Code table in `docs/META-MODELS.md` on this branch.
