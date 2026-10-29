"""Beat Mask local app. Run:  .venv/bin/python server.py   then open http://localhost:8765

Four steps: 1 upload clip + track  2 tap the subject (SAM 3.1)  3 pick an effect  4 export.
Standard library only (no web framework), so there is nothing extra to install.
"""
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


class H(BaseHTTPRequestHandler):
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
        dst.write_bytes(self._body())
        PROJECT.save_state(**{f"upload_{kind}": str(dst)})
        return self._json({"ok": True, "path": dst.name, "bytes": dst.stat().st_size})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            data = json.loads(self._body() or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        st = PROJECT.state()
        try:
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
            elif u.path == "/api/export":
                eff = data.get("effect", "glow")
                drive = data.get("drive") or None
                def go():
                    out = pipeline.export(PROJECT, eff, drive, progress=prog)
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
