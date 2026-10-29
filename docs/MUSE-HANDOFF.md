# Handoff — what's built, what's left, who does it

Updated Tue Oct 27 2026 (Claude). Submission due Wed Nov 4, 8:00 PM Central. Target: submit Nov 3.

## Built today (on main)

- Whole loop works end to end: ingest → segment → beat map → 3 effects → 1080×1920 MP4 with the track.
- SAM 3.1 client written against Meta's docs: file upload, tap → point prompt, forward tracking, streamed
  parse with Meta's official parser, box-local masks pasted into full frames.
- Offline fallback segmenter so everything runs before the key works.
- Local web app (4 steps) and a CLI.
- Smoke test for today's milestone.
- Tested here on a synthetic clip + 120 BPM drum loop: kicks and snares detected on every hit, effects stay
  inside the mask, background untouched, export plays.

**Not yet tested against the live API** — that needs Garrick's key. This is the first thing to run.

## Rules for every agent (Claude Code, Muse Code, Codex)

1. Read `CLAUDE.md` first. Scope is fixed: one loop, three effects, no timeline, no accounts.
2. **Only Claude Code commits to `main`.** Muse Code works on its own branch `muse/<task>` and hands back a
   diff or a list. Two agents editing the same files breaks the build and costs days.
3. Commit before handing the repo to another tool.
4. Never write keys into code, commits or chat.
5. Log every session in `docs/BUILD-LOG.md`, and every Muse Code task in the table in `docs/META-MODELS.md`.

## Task queue

### 0. Garrick — today, 10 minutes (blocks everything)
- Put the key in `.env`, run `.venv/bin/python scripts/sam_smoke_test.py`.
- Then on real footage: `.venv/bin/python scripts/sam_smoke_test.py --video <clip> --tap X,Y`
  (open `tmp/work/.../frame0.jpg` to pick X,Y, or just use the web app).
- Pick 3 test clips (10–30 s, one clear subject, your own footage) and 2 Garrick Jordan tracks.

### 1. Muse Code — tests (isolated, good first Muse task)
Branch `muse/tests`. Write pytest tests, no network:
- `beats.analyze` on `tmp/test_beat.wav`: 8 kicks within ±30 ms of 0,1,2…7 s; 8 snares at 0.5,1.5…
- `effects.envelope`: 1.0 at a hit, decays, picks the most recent hit, -1 index before the first hit.
- `segment.mask_to_frame`: a mask whose box runs off the frame edge is clipped, not crashed.
- `segment.parse_records` on the sample line in `docs/META-MODELS.md` → 2 records, ids "0" and "1".
- `pipeline` end to end with `--segmenter mock` on the synthetic media → MP4 exists, 1080×1920, has audio.

### 2. Claude Code — fix what the first live SAM run shows (Wed Oct 28)
Likely items: mask edge flicker (temporal smoothing: blend each mask with the previous 1–2), subject lost
mid-clip (re-prompt on a later frame with the same object id), upload size/time on 30 s clips.
**Milestone Wed night: exported video from real footage + real SAM masks.** If it isn't there, cut scope that night.

### 3. Muse Code — Muse Spark "vibe → effect plan" (stretch, only if ahead, pick this OR MIDI pads)
Branch `muse/vibe`. New file `beatmask/vibe.py`:
- `plan(vibe: str, beatmap: dict) -> {"effect": "glow|flash|stutter", "drive": "kicks|snares|beats", "intensity": 0..1, "why": str}`
- Model `muse-spark-1.3`, Chat Completions at `https://api.meta.ai/v1`, structured output (JSON schema).
- Send tempo + hit counts, not the whole beatmap.
- Wire into the UI as an optional text box above the effect buttons that pre-selects the effect.

### 4. Claude Code — tempo (Thu)
`librosa.beat.beat_track` misreads sparse loops (80.75 BPM on a 120 BPM test loop). Kicks/snares are right,
so derive the beat grid from them when the tracker disagrees. Only `stutter` uses beats by default.

### 5. Antigravity — click through the UI on a test branch, return a bug list. Gemini — check rendered MP4s:
"do the effects land on the kicks and snares? does the mask slip off the subject?" Bugs go back to Claude Code as one list.

### 6. Freeze Mon Nov 2. Demo video + submission Tue Nov 3.

### 7. Claude Code — render speed (Fri, with flicker fixes)
On the Intel Mac a frame takes ~0.17 s to render, so a 30 s clip is ~2.5 min. For the 2-minute stranger
test: encode with `h264_videotoolbox` (Mac hardware encoder) instead of libx264, and do the float blending at
half resolution inside the subject box. Measure before/after on a real 15 s clip.
