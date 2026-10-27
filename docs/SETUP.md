# Setup from zero (Intel Mac)

Everything lives on the external drive: `/Volumes/Garrick Dri/ReelCut AI/reel-studio-beat-mask`. Never the internal drive.

1. **Tools:** ffmpeg + ffprobe on PATH (installed at `~/.local/bin`), Python 3.12.
2. **Python env** (already created as `.venv`):
   ```bash
   cd "/Volumes/Garrick Dri/ReelCut AI/reel-studio-beat-mask"
   .venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
   ```
3. **Key:** get a Meta Model API key at dev.meta.ai/platform. `cp .env.example .env`, paste it after `MODEL_API_KEY=`.
   `.env` is git-ignored. Never paste the key into a chat, a commit or a screenshot.
4. **Prove it works:** `.venv/bin/python scripts/sam_smoke_test.py` → should end with `MILESTONE MET`.
5. **Run the app:** `.venv/bin/python server.py` → http://localhost:8765
6. **Test without real footage:** `.venv/bin/python scripts/make_test_media.py` makes `tmp/test_clip.mp4` + `tmp/test_beat.wav`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No API key` | `.env` missing or the line is `META_API_KEY=` with nothing after it. Either name works. |
| `HTTP 401` | Key wrong or revoked. Make a new one in the dashboard. |
| `HTTP 404 model_not_found` | Team doesn't have `sam-3.1` access yet. Ask in the hackathon Discord. |
| `HTTP 400 ... aspect ratio` | Coordinates not in 1080×1920 space. Only happens if ingest was skipped. |
| Zero masks | Tap landed on background. Tap the middle of the subject. |
| UI says "server offline" | `server.py` isn't running, or another app has port 8765 (`PORT=8770 .venv/bin/python server.py`). |
