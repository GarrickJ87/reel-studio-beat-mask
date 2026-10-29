# Recording plan: the 3-minute demo, one take at a time

Rules for every take (from the hackathon rules and Garrick's notes):
- Show only work built Oct 26 - Nov 4. Show the app and the computer running themselves.
- Never show a key, `.env`, the Meta dashboard, billing, or the private `reel-studio` repo.
- Save every take to `/Volumes/Garrick Dri/ReelCut AI/reel-studio-build-footage/raw/` named `T1_...`, `T2_...`.
- Voice: record in a quiet room; every voice track goes through Adobe Enhance Speech before the edit.
- No music while recording; music goes on at the end.

Screen takes: press **Cmd+Shift+5**, choose **Record Selected Portion** (just the browser or terminal window),
**Options -> Microphone: None** (voiceover is recorded separately), then Record. Stop with the stop button in the menu bar.
Before each screen take: close other windows, hide the Dock (Cmd+Option+D), browser zoom so text is readable, terminal font 18+.

| Take | What to record | How | Length on screen | Voiceover line (draft, say it your way) |
|---|---|---|---|---|
| T1 | The result, no talking | nothing to record: the edit uses `renders/garrick_hallway_glow.mp4` | 0:00-0:10 | (none, let the beat play) |
| T2 | You, to camera or voice only | phone or QuickTime (File -> New Movie Recording), plain background | 0:10-0:30 | "I'm Garrick Jordan, a producer and video editor. Beat-sync tools cut the whole frame. I wanted effects that play the person, not the frame." |
| T3 | Live app, part 1: upload + tap | screen: http://127.0.0.1:8765, upload `media/garrick_clip.mp4` and the track, offset 15, Analyze, tap your face, Find subject | 0:30-1:00 (cut the waiting) | "One clip, one track. I tap myself once. SAM 3.1, Meta's segmentation model, finds me and tracks me through every frame." |
| T4 | Live app, part 2: effect + export | same screen: pick Glow, Export, wait for "verified 6/6 checks", play the export | 1:00-1:35 (cut the render wait) | "Pick an effect. Glow hits on the kicks, only on me. Before the file is handed over, the app checks its own work." |
| T5 | Under the hood: verification | terminal in the repo: `cat renders/garrick_hallway_glow.mp4.verify.json` scrolled slowly, then `.venv/bin/python -m pytest -q` (25 passed) | 1:35-2:05 | "Every export is checked inside the export step: effect inside the mask, background untouched, every beat proven. Three tries, then it comes to me, and nothing is final until I sign off." |
| T6 | Muse Code at work | terminal: `git log --oneline --grep=Muse`, then `cat docs/MUSE-TASK-verify-tests.md`; and the workshop Agent Console showing the signed-off run | 2:05-2:35 | "I built it with Muse Code: it wrote the test suites and reviewed the verification layer, and I used the same pattern in Meta's agent workshop." |
| T7 | Second result + end card | nothing to record: `renders/garrick_hallway_flash.mp4` + the end card | 2:35-3:00 | "Beat Mask is the first module for Reel Studio. Built for Meta's Global AI Developer Hackathon." |

Timing: about 3:00. T3 and T4 have long waits (SAM ~40 s, render + checks ~3 min); keep recording and the edit cuts the waits.
When a take is saved, tell Claude the file name; Claude checks it (length, no secrets on screen, audio) before the edit.
