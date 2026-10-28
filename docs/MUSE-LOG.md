# Muse log: every step where Meta's tools were used

Kept for the Meta Global AI Developer Hackathon submission. Times are Central. Everything here is also in git history or `docs/BUILD-LOG.md`.
Who did what is stated plainly: Claude Code (the builder) wrote and committed most of the code; Muse Code did one real task on its own branch; SAM 3.1 is the core of the app.

## Meta Model API

| When | What | Result |
|---|---|---|
| Oct 26 | API key created in the Meta Model API dashboard (key named Playground) | free credits applied |
| Oct 27 | Workshop repo `meta-models/legal-agent-workshop`: `./helper setup` preflight | "MODEL_API_KEY works: muse-spark-1.3 and sam-3.1 are available" |
| Oct 27 | `scripts/sam_smoke_test.py`: `GET /v1/models` | key OK; models listed: sam-3.1, muse-spark-1.3, muse-wonder-1.0, others |
| Oct 27 | SAM 3.1 image call (`POST /v1/responses`, model `sam-3.1`) | 1 mask, 6.5% of frame: **milestone met** |
| Oct 27 | SAM 3.1 video, point prompt, forward tracking, synthetic clip | 240/240 frames tracked in 71 s |
| Oct 28 | SAM 3.1 video on Garrick's real clip (tap on face, frame 0) | 206/206 frames, head, shirt and hand covered, ~40 s |
| Oct 28 | Full pipeline, real clip + Odd Wilson "Playing in the Hallway" | glow on kicks, flash on snares, 1080x1920 export |

How SAM 3.1 is used (details in `docs/META-MODELS.md`): file upload, then one request with the tap as a point prompt, streamed back as one mask per frame.
Not used: Muse Spark (vibe to effect plan) is a stretch goal and is not built; it will only be claimed if it ships.

## Muse Code

| When | What | Result |
|---|---|---|
| Oct 27 13:45 | Installed Muse Code (`curl https://dev.meta.ai/install.sh`; script read before running) | `muse` at `~/.local/bin/muse` |
| Oct 27 13:48 | Wrote the task brief `docs/MUSE-TASK-tests.md` on branch `muse/tests` (Claude) | five offline test areas, no network, report bugs instead of fixing |
| Oct 27 ~14:00-14:13 | **Muse Code wrote the pytest suite** (commit `dca2e11`) | `tests/` with 11 tests; 10 passed, 1 expected failure |
| Oct 27 | Muse's test found a real bug: `mask_to_frame` crashed when SAM's box was fully off the frame | reported, not fixed on its branch (as briefed) |
| Oct 27 14:23 | Claude reviewed the branch, merged it to `main`, fixed the bug (`0304077`); test now passes | 11 tests green |
| Oct 28 | Muse's suite grew to 14 tests with the tempo tests (Claude) | 14 passed |

Muse Code's contribution: the offline test suite, and the bug it found. Everything else in the app was built by Claude Code.

## Muse (chat assistant) reviews

The Muse chat assistant did a code review and account checks on Oct 27, recorded in the "flush-out package" (public repo state, dashboard balance, form status). I did not redo those checks; I used them as stated and verified the local pieces myself.

## What the Muse steps taught us

- Muse Code is good at isolated, well-briefed tasks with a clear "done when": tests are the right first task.
- Its tests caught a bug the first build missed.
- The pure-Python mask decoder in `meta-sam-parser` is too slow on an Intel Mac (13 s per mask); `beatmask/fastmask.py` is a bit-exact numba replacement (see BUILD-LOG).
