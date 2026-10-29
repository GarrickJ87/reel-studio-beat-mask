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
| Oct 28 | Full pipeline, real clip + Garrick Jordan "Playing in the Hallway" | glow on kicks, flash on snares, 1080x1920 export |

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

| Oct 28 | **Muse Code as reviewer** (Day 3: a second session with review-only access), headless `muse exec` in a detached worktree, on the new export verification layer | ~20 findings, one line each; it edited nothing (worktree clean afterwards) |
| Oct 28 | Claude applied the valid findings on `main` (`122ff06`): removed the switch that let an export skip verification, fixed retries at 3, bound sign-off to the export's SHA-256, required every claimed beat, measured stutter instead of skipping it, used the clip's real fps, kept `--out` inside the project | all three real exports still pass the stricter checks |
| Oct 28 | Findings not taken, with reasons: the dilation kernel is already the right size at quarter resolution; a sign-off gate on web downloads would break the clip-to-export flow; the centroid limit (90 px) is above the worst jump measured on the real clip (46 px) | recorded here |
| Oct 28 | **Muse Code task 2**, branch `muse/verify-tests` (brief `docs/MUSE-TASK-verify-tests.md`): 11 offline tests for `beatmask/verify.py` and the render smoothing (`b791162`) | 11 passed, no app code touched |
| Oct 28 | Claude's review of task 2: Muse's tests replaced `cv2.VideoCapture` with an ffmpeg-pipe fake because a probe said OpenCV can't read H.264 here. The probe was wrong (it wrote the sample with OpenCV's VideoWriter, which can't write MP4 in this build; reading works). Fixed the probe to make the sample with ffmpeg, so the real reader is tested. Merged (`549c3d3`) | 11/11 still pass on the real code; full suite 25 passed |

Muse Code's contribution so far: two offline test suites (the first found a real crash), and a review-only pass whose findings hardened the export verification layer. The rest of the app was built by Claude Code under Garrick's direction.

## Meta workshop (Day 2 + Day 3), built with Muse Code

Repo `meta-models/legal-agent-workshop`, run on Garrick's Mac (separate from Beat Mask; kept here as Muse/Model API evidence). Muse Code was started from `agent/` only, with the HANDBOOK 1.7 ground rules as its first message each session, then the HANDBOOK prompts, one at a time.

| When | What | Result |
|---|---|---|
| Oct 28 | Session 1, Muse Code: plan the agent loop (no code), then build `legal_agent/loop.py` | only `loop.py` changed; workshop offline tests OK |
| Oct 28 | Session 1 run, `muse-spark-1.3` via the Model API (`run-20261029T004734Z-f97797`) | 22 turns, 6-item checklist, 21 documents read, 11 facts, memo filed **unverified** |
| Oct 28 | Session 2, Muse Code: build the memo rules (`verification/verify_memo.py`) and the checklist check (`verification/verify_checklist.py`) | verification tests 58 OK |
| Oct 28 | Verify the Session 1 work | memo FAIL (2 unsupported claims); checklist FAIL, 50% ground-truth coverage |
| Oct 28 | Continue from the checklist with verification on (`run-20261029T010752Z-538a77`) | checklist refused, revised to 83%; memo refused 3 times, escalated to a person; privileged document flagged and not cited |
| Oct 28 | Garrick replied to the escalation (R1) as reviewer, the agent refiled | memo passed the memo rules and the claims check |
| Oct 28 | **Garrick signed off as the attorney** in the Agent Console | run **done**, memo **approved** |

The pattern Beat Mask copies from this: checks inside the step that ships the work (not optional tools), max 3 refusals then a person, human sign-off last.

## Muse (chat assistant) reviews

The Muse chat assistant did a code review and account checks on Oct 27, recorded in the "flush-out package" (public repo state, dashboard balance, form status). I did not redo those checks; I used them as stated and verified the local pieces myself.

## What the Muse steps taught us

- Muse Code is good at isolated, well-briefed tasks with a clear "done when": tests are the right first task.
- Its tests caught a bug the first build missed.
- The pure-Python mask decoder in `meta-sam-parser` is too slow on an Intel Mac (13 s per mask); `beatmask/fastmask.py` is a bit-exact numba replacement (see BUILD-LOG).
