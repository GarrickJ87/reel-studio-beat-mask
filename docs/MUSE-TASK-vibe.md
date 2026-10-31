# Muse Code task 3: Muse Spark "vibe -> effect plan" (branch `muse/vibe`)

Read `AGENTS.md` first. Work ONLY in this worktree. Create ONLY `beatmask/vibe.py` and `tests/test_vibe.py`, plus one row in the
Muse Code table in `docs/META-MODELS.md`. Do NOT edit `render.py`, `pipeline.py`, `server.py` or `static/` (Claude wires those).
Never open `.env`, never print or log a key. Tests must be offline (no network).
Run tests with: `"/Volumes/Garrick Dri/ReelCut AI/reel-studio-beat-mask/.venv/bin/python" -m pytest tests/test_vibe.py -q`

## What to build: `beatmask/vibe.py`

`plan(vibe: str, beatmap: dict, post=None) -> dict` returns `{"effect": "glow"|"flash"|"stutter", "drive": "kicks"|"snares"|"beats", "intensity": float in [0, 1], "why": str}`.

Verified API facts (tested live Oct 31 by Claude, use exactly these):
- `POST {config.BASE_URL}/chat/completions` with header `Authorization: Bearer {config.api_key()}` and JSON body:
  `{"model": config.SPARK_MODEL, "messages": [system, user], "reasoning_effort": "low", "response_format": {"type": "json_schema", "json_schema": {"name": "plan", "strict": true, "schema": SCHEMA}}}`
- SCHEMA: object with `effect` (enum glow/flash/stutter), `drive` (enum kicks/snares/beats), `intensity` (number), `why` (string); all required; `additionalProperties: false`.
- The reply text is `response["choices"][0]["message"]["content"]`, a JSON string. Low effort answers in about 4 s.

Rules:
- Send a short summary of the track, not the beat lists: tempo, duration, number of kicks, snares and beats (from the beatmap dict: keys `tempo`, `duration`, `kicks`, `snares`, `beats`).
- The system prompt explains the three effects in one line each (glow = subject brightens and blooms on hits; flash = subject washed in color on hits; stutter = subject freezes with a color split on hits) and asks for JSON only. Nothing case-specific.
- Validate the reply: effect and drive must be in their enums, intensity is clamped to [0, 1], `why` trimmed to 200 characters. Anything invalid or a non-200 status raises `VibeError` with a short message (never include the key or the full response).
- Empty or whitespace `vibe` raises `VibeError` without calling the API.
- `post` is injectable (default `requests.post`) so tests can pass a fake; use `timeout=60`.

## Tests: `tests/test_vibe.py` (fake `post`, no network)
1. A valid reply is parsed into the dict with the right types.
2. intensity 1.7 is clamped to 1.0 and -0.2 to 0.0.
3. An effect outside the enum raises `VibeError`.
4. A non-200 status raises `VibeError`, and the error text does not contain the Authorization header value.
5. The request body sent to `post` has model `muse-spark-1.3` (from config), `reasoning_effort` "low", the json_schema format, and the user message contains the tempo and the counts but not the raw beat lists.
6. Empty vibe raises `VibeError` and `post` is never called.

Done when: both files exist, tests pass, the META-MODELS row is added, committed on `muse/vibe`. Hand back: files changed, test results, any limitation.
