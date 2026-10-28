# Demo shot list: what to record, in order

Target: **3 minutes with voiceover** (the Participant Guide asks for a well-produced three-minute demo). It must show only work built Oct 26 - Nov 4, and no keys, `.env`, dashboard or account screens.
The 7 scenes below are the spine (~2 min); add voiceover and one longer live run to reach about 3 minutes.

Record screen + voice with macOS Cmd+Shift+5 (or QuickTime). Keep each take on its own so we can cut it together. No music while recording; it goes on at the end.

| # | Scene | Record | Length |
|---|---|---|---|
| 1 | The result | Play `renders/garrick_hallway_glow.mp4` full screen | 8 s |
| 2 | The problem | Face to camera or voiceover: beat-sync tools cut the whole frame, never the person | 15 s |
| 3 | Live run | `http://localhost:8765`: upload clip + track, tap the subject, watch SAM mask appear, pick glow, export | 40 s |
| 4 | Under the hood | Terminal: `scripts/demo_run.sh` (banners per stage), then the side-by-side tracking | 20 s |
| 5 | Muse Code | Terminal: `git checkout muse/tests && muse`, show `docs/MUSE-TASK-tests.md`, then `pytest` green | 15 s |
| 6 | Second result | `renders/garrick_hallway_flash.mp4` | 8 s |
| 7 | End card | Beat Mask, a Reel Studio plug-in; Meta SAM 3.1 via the Model API; Muse Code; repo link | 5 s |

Before each take: close other windows, hide the Dock, use a light terminal font size 18+, run `git status` clean.
Pre-render the full clip first so the live run (scene 3) uses a short clip; the full pipeline takes about 6 minutes on this Mac.
