"""Settings read from the environment (and .env in the repo root). Keys are never hard-coded."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get("BEATMASK_WORK_DIR", ROOT / "tmp" / "work"))


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if value and key not in os.environ:
            os.environ[key] = value


load_dotenv()

BASE_URL = os.environ.get("META_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/")
SAM_MODEL = os.environ.get("SAM_MODEL", "sam-3.1")
SPARK_MODEL = os.environ.get("MUSE_SPARK_MODEL", "muse-spark-1.3")

# Output format: 1080x1920 vertical, 30 fps, clips capped at 30 s.
OUT_W, OUT_H, FPS, MAX_SECONDS = 1080, 1920, 30, 30


def api_key() -> str | None:
    """Meta's docs call it MODEL_API_KEY; the plan used META_API_KEY. Accept either."""
    return os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY") or None


def ffmpeg() -> str:
    return os.environ.get("FFMPEG_PATH", "ffmpeg")


_ENCODER = None


def video_encoder_args() -> list[str]:
    """Mac hardware H.264 encoder when this ffmpeg has it (faster on a laptop), else libx264."""
    global _ENCODER
    if _ENCODER is None:
        import subprocess
        try:
            out = subprocess.run([ffmpeg(), "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        want = os.environ.get("BEATMASK_ENCODER", "auto")
        _ENCODER = "h264_videotoolbox" if want != "libx264" and "h264_videotoolbox" in out else "libx264"
    if _ENCODER == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-b:v", "12M", "-allow_sw", "1"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]


def ffprobe() -> str:
    return os.environ.get("FFPROBE_PATH", "ffprobe")
