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
| | | | |
