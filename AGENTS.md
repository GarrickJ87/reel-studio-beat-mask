# Beat Mask — Reel Studio plug-in (Meta Global AI Developer Hackathon)

## What we're building
A single plug-in module for Reel Studio. The user loads a short clip and an audio track, taps a subject, picks an effect, and exports a video where the effect hits only the subject, on the beat. The background stays untouched.

Hackathon: Meta Global AI Developer Hackathon (Cerebral Valley), Indie track, theme "Build for Your World." Runs Oct 26 – Nov 4, 2026. Submission due Wed Nov 4, 9:00 PM ET (8:00 PM Central). Target: submit Nov 3.

## The one loop that must work
1. Ingest — browser upload of 1 clip (≤30 sec) + 1 audio track; extract frames with ffmpeg.
2. Segment — user taps subject on frame 1; SAM 3.1 (Meta Model API) returns the mask and tracks it across frames.
3. Beat map — detect beats and onsets (kick/snare) with librosa; output a list of hit times. No AI needed here.
4. Render — apply the chosen effect only inside the mask on each hit; ffmpeg reassembles with the audio.
5. Export — 1080×1920 MP4 download.

Get an ugly version of all five working end to end before improving any one of them. Milestone: exported video by Wed Oct 28.

## Scope
Must ship: upload, tap-to-segment with SAM 3.1, beat/onset detection, 3 mask-only effects (glow pulse, color flash, stutter), 1080p vertical MP4 export.

Stretch (only if ahead, pick one): Muse Spark turns a text vibe ("make it aggressive") into an effect plan · MPC/MIDI pads trigger effects live · multiple subjects · live preview.

Out — do not build: full timeline/NLE, rack/console UI, 4K, color grading, accounts, payments, sharing, branding polish.

Definition of done: a stranger goes from clip to exported video in under 2 minutes without help.

## Meta models (judges score their use)
- SAM 3.1 — core: segmentation and tracking.
- Muse Spark — stretch: vibe-to-effect plan.
- Muse Code — used for at least one real task; mention in submission.
- Open question for day 1: does SAM 3.1 video tracking run through the Model API, or do we need open weights on Modal/Baseten credits? Fallback: segment keyframes and interpolate.

## Working rules
- This repo starts fresh and standalone so pre-existing-code rules can't hurt the entry.
- Claude Code is the only tool that writes to main. Codex reviews PRs and takes isolated tasks on its own branch. Antigravity tests the UI on a test branch. Gemini checks rendered MP4s. Bugs from other tools come back here as one pasted list.
- Commit after every working step, and before handing the repo to any other tool.
- Never commit API keys. Keys live in .env (gitignored); provide .env.example.
- Use only the developer's own footage and Odd Wilson tracks — no copyrighted media in tests or the demo.
- Prefer the simplest thing that works. If a stage blocks for more than one session, cut scope and keep the loop alive.
- All project files, media, renders and caches stay on /Volumes/Garrick Dri. Never write to the internal drive.

## Developer context
Solo developer working around a 4:00 AM–12:45 PM shift. Sessions are short (2–3 hours, evenings) with longer ones on days off. Start each session by stating where the build is against the day plan and the single next step.

## Day plan
| Day | Session | Done when |
| --- | --- | --- |
| Mon Oct 26 | Kickoff, Discord, API keys, partner credits | One SAM 3.1 call returns a mask |
| Tue Oct 27 | Ingest + Segment | Mask tracks a subject through a 10-sec clip |
| Wed Oct 28 | Beat map + glow effect + export | Ugly end-to-end video exported |
| Thu Oct 29 | Color flash + stutter | All 3 effects clean on 3 test clips |
| Fri Oct 30 | Mask edge flicker, timing sync | Effects land on the beat, no lag |
| Sat Oct 31 | UI pass: simple 4-step flow | Stranger test under 2 min |
| Sun Nov 1 | One stretch goal | Works, or cut it |
| Mon Nov 2 | Feature freeze, record demo | 2-min demo exported |
| Tue Nov 3 | README, submission, cleanup | Submitted |
| Wed Nov 4 | Buffer only | Fixes only |
