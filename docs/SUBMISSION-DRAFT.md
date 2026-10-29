# Submission draft — NOT SUBMITTED

Draft for the Cerebral Valley "Submit Project" form, Meta Global AI Developer Hackathon.
Nothing here has been submitted. Garrick gives the final yes and fills the PLACEHOLDER fields.
Hard deadline: Wed Nov 4, 9:00 PM ET / 8:00 PM CT. Freeze Nov 2, target submit Nov 3.

| Field | Value |
|---|---|
| Team name | PLACEHOLDER |
| Contributors | Garrick Jordan (solo) |
| Track | Indie Developer Track |
| Problem statement / theme | Build for Your World |
| Project name | Beat Mask (a Reel Studio module) |
| Public repository | https://github.com/GarrickJ87/reel-studio-beat-mask |
| Demo video (about 3 min, voiceover) | PLACEHOLDER |
| License | PLACEHOLDER |
| Meta models and tools used | SAM 3.1 via the Meta Model API (core); Muse Code (coding agent: test suites and a review-only pass) |

## One-liner

Tap a subject once: SAM 3.1 isolates and tracks it, and effects hit only that subject, locked to the kicks and snares, while the background stays untouched.

## Description

Beat-sync tools cut or flash the whole frame. Beat Mask makes the effect play the person instead.

1. Load one short clip and one track.
2. Tap the subject on the first frame. That tap is sent to **SAM 3.1 through the Meta Model API** as a point prompt; SAM segments the subject and tracks it forward through every frame (one hosted call, no GPU or open weights needed).
3. The track is analysed for kicks and snares.
4. Pick an effect: **glow** (the subject brightens and blooms on each kick) or **color flash** (on each snare). The effect is applied only inside the subject's mask.
5. Export a 1080x1920 MP4 with the track.

**The export checks itself before it is handed over** (the Day 3 "verifiable agents" lesson, applied to video): the checks run inside the export step, so they cannot be skipped. Deterministic checks: format, subject present, background untouched, every claimed beat shows the effect inside the mask. Judge-style checks measured from the frames: the mask doesn't flicker or slip, and the subject isn't lost. A failed check re-renders with stronger mask smoothing, at most 3 attempts, then escalates to a person. Nothing is final until a human signs off, and the sign-off is bound to the exact file's hash.

## What was built when (new work only)

- **Oct 25:** one setup-only commit (project brief, `.gitignore`, `.env.example`, requirements). No app code.
- **Oct 27 - Nov 4:** all application code: ingest, the SAM 3.1 client and a fast bit-exact mask decoder, beat map and tempo fix, the effects, renderer and export, the verification layer, the web app, the tests and docs.
- Standalone project. No code from the existing Reel Studio product, and no pre-existing Meta Vision slot, is included or presented.
- The sample clip and the music are Garrick Jordan's own.

## How Meta's tools were used (details: `docs/MUSE-LOG.md`, `docs/META-MODELS.md`)

- **SAM 3.1 (Meta Model API):** subject segmentation and video tracking from a single tap; the core of the app. Real clip tracked on 206/206 frames.
- **Muse Code:** wrote two offline test suites on their own branches (the first found a real crash), and did a review-only pass on the verification layer whose findings hardened it. Also used through Meta's agent workshop (Days 2-3) to build an agent loop and its verification checks.
- Built by Garrick Jordan with Claude Code and Muse Code as assistants under his direction.
- Not claimed: Muse Spark (not built in this repo).

## Before submitting (Garrick)

- [ ] Team name, demo video link, license filled in above
- [ ] Demo video uploaded somewhere judges can open it (for example unlisted YouTube or Vimeo)
- [ ] Final read of README and this text
- [ ] Final yes
