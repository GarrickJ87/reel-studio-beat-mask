# How Beat Mask uses Meta's models

Written for judges and for whoever (human, Claude Code or Muse Code) works on the integration next.
Source: Meta Model API docs at dev.meta.ai/docs (SAM overview, Segmenting with prompts, Reading segmentation output), read Oct 27 2026.

## SAM 3.1 — the core (`beatmask/segment.py`)

- **Endpoint:** `POST https://api.meta.ai/v1/responses`, `model: "sam-3.1"`, Bearer key (env `MODEL_API_KEY`). OpenAI-SDK compatible.
- **Upload once:** the normalized clip goes to `POST /v1/files` (`purpose=user_data`), then is referenced as
  `{"type": "input_video", "file_id": "..."}`. Clips are exported with `+faststart` so the service doesn't remux.
- **The tap is a point prompt**, not a text prompt. The `input_text` part carries SAM's token grammar:
  `<0f>1<|point;x=540;y=900;w=1080;h=1920|>` — object id 1, frame 0, coordinates in media pixels.
  Built with Meta's `build_object_prompt` from the `meta-sam-parser` package.
  - Never mix a noun phrase with point/box prompts in one request (400 error).
  - `w`/`h` must match the media's aspect ratio (400 otherwise). We always send 1080×1920 because ingest normalizes to it.
- **Metadata:** `propagation_direction: "forward"` (track from the tap frame to the end; cheaper than `both`),
  `mask_encoding: "one_bit"` (point prompts always return one_bit anyway).
- **Response:** streamed SSE. Each `response.output_text.delta` is one frame:
  `<Nf>id<|box;x1;y1;x2;y2;w;h|><|mask;x=0;y=0;data=H,W,!payload|>`. Frames with nothing visible are skipped,
  so we key masks by the `<Nf>` marker, never by line order. Masks are **box-local** and base85; we decode with
  `decode_mask_to_raster`, resize to the box, and paste into a full 1080×1920 frame (`mask_to_frame`).
- **Zero matches is valid** (empty output, `response.completed`). Treated as "subject not found", not a crash.
- **Speed note:** the official parser decodes masks in pure Python (~13 s each on an Intel Mac); `beatmask/fastmask.py` is a bit-exact numba decoder swapped in at import.
- **Limits:** MP4/MOV, H.264/H.265/MPEG-4 (no VP9/WebM); ≤15,000 frames; ≤16 tracked objects.
- **Cost:** $0.20 per 1,000 video frames, 50-frame minimum per request. A 30 s clip at 30 fps = 900 frames ≈ $0.18.
  Image calls $2.50 per 1,000 images.

## Muse Spark — stretch (not built yet, see MUSE-HANDOFF.md task 3)

Turn a text vibe ("make it aggressive") into an effect plan: which effect, which drum drives it, intensity.
Model `muse-spark-1.3` over Chat Completions with structured output. Meta's own docs recommend exactly this
pairing: Muse Spark interprets, SAM 3.1 segments.

## Muse Code — used as a coding agent on real tasks

Meta built the event around its own tools. Muse Code takes isolated tasks on their own branches
(see MUSE-HANDOFF.md). Record which tasks it did here, for the submission:

| Date | Task | Branch | Result |
|---|---|---|---|
| Tue Oct 27 | Offline pytest suite (beats, envelope, segment, mock e2e) | muse/tests | 10 passed, 1 xfail; fully-off-frame mask_to_frame crash found by its test; fixed on main by Claude Code |
| Wed Oct 28 | Offline pytest suite for the export verification layer (verify.py) | muse/verify-tests | 11 passed: check_format (pass/wrong-size/no-audio), verify_export pass + 4 named-check failures, signoff refuse/approve, render smooth=2 hole fill |
| Wed Oct 28 | Review-only pass on the export verification layer (verify.py, pipeline.export, render smoothing, server) | detached worktree, no edits | ~20 findings; the valid ones applied on main by Claude Code in 122ff06 (see MUSE-LOG.md) |
| Wed Oct 28 | Meta workshop: built the agent loop and both verification checks (HANDBOOK prompts, from agent/) | legal-agent-workshop | Session 1 memo filed; Session 2 run signed off by Garrick, status done (see MUSE-LOG.md) |
