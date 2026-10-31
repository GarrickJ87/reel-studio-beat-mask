"""Beat Mask local app. Run:  .venv/bin/python server.py   then open http://localhost:8765

Four steps: 1 upload clip + track  2 tap the subject (SAM 3.1)  3 pick an effect  4 export.
Standard library only (no web framework), so there is nothing extra to install.
"""
import hmac
import json
import mimetypes
import os
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from beatmask import config, effects, pipeline

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
UPLOADS = config.WORK / "uploads"
PORT = int(os.environ.get("PORT", "8765"))

JOB = {"stage": "idle", "progress": 0.0, "message": "", "error": None}
LOCK = threading.Lock()
PROJECT = pipeline.Project("app")


def set_job(**kw):
    with LOCK:
        JOB.update(kw)


def run_job(stage, fn):
    def wrapped():
        set_job(stage=stage, progress=0.0, message=f"{stage}...", error=None)
        try:
            msg = fn()
            set_job(stage=f"{stage}:done", progress=1.0, message=msg or "done")
        except Exception as e:  # surface every failure in the UI, never a silent hang
            traceback.print_exc()
            set_job(stage=f"{stage}:error", error=str(e), message=str(e)[:400])
    if JOB["stage"] in ("ingest", "segment", "export"):
        raise RuntimeError("a job is already running")
    threading.Thread(target=wrapped, daemon=True).start()


def prog(done, total):
    set_job(progress=min(done / max(total, 1), 0.99))


# Optional passcode for sharing the app through a temporary tunnel (stranger test). Off unless set.
PASSCODE = os.environ.get("BEATMASK_PASSCODE", "")
MAX_UPLOAD = 500_000_000  # bytes; a 30 s 4K iPhone clip is well under this
LOCK_PAGE = b"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1"><title>Beat Mask</title>
<body style="font:16px -apple-system,sans-serif;background:#0f1216;color:#e7eaee;display:grid;place-items:center;height:100vh;margin:0">
<form method="get" action="/" style="text-align:center"><h2>Beat Mask</h2><p>Enter the passcode you were given.</p>
<input name="code" autofocus style="padding:10px;border-radius:8px;border:1px solid #333;font-size:16px">
<button style="padding:10px 16px;margin-left:6px;border:0;border-radius:8px;background:#ff3fc8;font-weight:600">Open</button></form></body>"""


class H(BaseHTTPRequestHandler):
    def _allowed(self) -> bool:
        """True when no passcode is set, or the request carries it (cookie, or ?code= on the first visit)."""
        if not PASSCODE:
            return True
        cookie = self.headers.get("Cookie", "")
        have = next((c.split("=", 1)[1] for c in cookie.split("; ") if c.startswith("bm_pass=")), "")
        return hmac.compare_digest(have, PASSCODE)

    def _locked(self):
        u = urlparse(self.path)
        code = parse_qs(u.query).get("code", [""])[0]
        if u.path == "/" and code and hmac.compare_digest(code, PASSCODE):
            self.send_response(303)
            self.send_header("Set-Cookie", f"bm_pass={PASSCODE}; Path=/; HttpOnly; SameSite=Strict")
            self.send_header("Location", "/")
            self.end_headers()
            return
        if u.path == "/":
            self.send_response(200 if not code else 403)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(LOCK_PAGE)
            return
        self._json({"error": "passcode required"}, 401)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, download=False):
        if not path.exists() or not path.is_file():
            return self._json({"error": "not found"}, 404)
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        with open(path, "rb") as f:
            while chunk := f.read(1 << 20):
                self.wfile.write(chunk)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        if not self._allowed():
            return self._locked()
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._file(STATIC / "index.html")
        if u.path == "/api/status":
            st = PROJECT.state()
            return self._json({"job": JOB, "state": st, "has_key": bool(config.api_key()),
                               "effects": list(effects.EFFECTS), "default_drive": effects.DEFAULT_DRIVE})
        if u.path.startswith("/work/"):
            name = Path(u.path[len("/work/"):]).name  # no path traversal: file names only
            q = parse_qs(u.query)
            return self._file(PROJECT.dir / name, download="dl" in q)
        return self._json({"error": "not found"}, 404)

    def do_PUT(self):
        if not self._allowed():
            return self._locked()
        u = urlparse(self.path)
        if u.path != "/api/upload":
            return self._json({"error": "not found"}, 404)
        q = parse_qs(u.query)
        kind = q.get("kind", [""])[0]
        if kind not in ("clip", "track"):
            return self._json({"error": "kind must be clip or track"}, 400)
        ext = Path(q.get("name", ["x.bin"])[0]).suffix.lower()[:6] or ".bin"
        UPLOADS.mkdir(parents=True, exist_ok=True)
        dst = UPLOADS / f"{kind}{ext}"
        # Chunked: the page sends 8 MB pieces with offset/total, because tunnels (Cloudflare: 100 MB) cap one request.
        try:
            offset = int(q.get("offset", ["0"])[0]); total = int(q.get("total", ["-1"])[0])
        except ValueError:
            return self._json({"error": "bad offset/total"}, 400)
        if total > MAX_UPLOAD:
            return self._json({"error": f"file is {total / 1e6:.0f} MB; the limit is {MAX_UPLOAD / 1e6:.0f} MB. Trim it to 30 s or less."}, 413)
        have = dst.stat().st_size if dst.exists() and offset else 0
        if offset != have:
            return self._json({"error": f"upload out of order (got offset {offset}, have {have}); pick the file again"}, 409)
        data = self._body()
        with open(dst, "r+b" if offset else "wb") as f:
            f.seek(offset)
            f.write(data)
        size = dst.stat().st_size
        print(f"[upload] {kind}{ext}: {offset}+{len(data)} -> {size} of {total} bytes", flush=True)
        if total < 0 or size >= total:
            PROJECT.save_state(**{f"upload_{kind}": str(dst)})
        return self._json({"ok": True, "path": dst.name, "bytes": size, "done": total < 0 or size >= total})

    def do_POST(self):
        if not self._allowed():
            return self._locked()
        u = urlparse(self.path)
        try:
            data = json.loads(self._body() or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        st = PROJECT.state()
        try:
            if u.path == "/api/reset":
                if JOB["stage"] in ("ingest", "segment", "export"):
                    return self._json({"error": "a job is still running"}, 409)
                set_job(stage="idle", progress=0.0, message="", error=None)
                return self._json({"ok": True})
            if u.path == "/api/ingest":
                if not st.get("upload_clip") or not st.get("upload_track"):
                    return self._json({"error": "upload a clip and a track first"}, 400)
                off = float(data.get("track_offset", 0) or 0)
                def go():
                    s = pipeline.ingest(PROJECT, Path(st["upload_clip"]), Path(st["upload_track"]), off)
                    return f"{s['frames']} frames · {s['tempo']} BPM · {s['n_kicks']} kicks · {s['n_snares']} snares"
                run_job("ingest", go)
            elif u.path == "/api/segment":
                x, y = int(data["x"]), int(data["y"])
                kind = data.get("segmenter", "auto")
                def go():
                    s = pipeline.segment_subject(PROJECT, x, y, kind, progress=prog)
                    return f"{s['segmenter']}: subject found on {s['mask_frames']}/{s['frames']} frames ({s['segment_seconds']}s)"
                run_job("segment", go)
            elif u.path == "/api/vibe":
                # Muse Spark turns a typed vibe into an effect plan; quick (~4 s), so it answers directly
                from beatmask import vibe
                if not PROJECT.beatmap.exists():
                    return self._json({"error": "load a clip and a track first"}, 400)
                try:
                    plan = vibe.plan(str(data.get("vibe", "")), json.loads(PROJECT.beatmap.read_text()))
                except vibe.VibeError as e:
                    return self._json({"error": str(e)}, 400)
                PROJECT.save_state(vibe_plan=plan)
                return self._json({"ok": True, "plan": plan})
            elif u.path == "/api/export":
                eff = data.get("effect", "glow")
                drive = data.get("drive") or None
                intensity = float(data.get("intensity", 1.0) or 1.0)
                def go():
                    out = pipeline.export(PROJECT, eff, drive, progress=prog, intensity=intensity)
                    PROJECT.save_state(last_export_name=out.name)
                    r = json.loads(Path(str(out) + ".verify.json").read_text())
                    checks = [c for c in r["checks"] if c["pass"] is not None]
                    ok = sum(1 for c in checks if c["pass"])
                    return f"{out.name} · verified {ok}/{len(checks)} checks (attempt {r['attempt']}) · sign-off pending"
                run_job("export", go)
            else:
                return self._json({"error": "not found"}, 404)
        except RuntimeError as e:
            return self._json({"error": str(e)}, 409)
        return self._json({"ok": True})


if __name__ == "__main__":
    print(f"Beat Mask running at http://localhost:{PORT}  (SAM key loaded: {bool(config.api_key())})")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
