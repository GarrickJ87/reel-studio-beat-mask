"""Shared fixtures for Beat Mask's offline tests. No network, no API key.

Everything these tests read or write lives under the repo's tmp/ (gitignored,
on the external drive): synthetic media in tmp/, run folders in tmp/work/.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def test_media():
    """tmp/test_clip.mp4 + tmp/test_beat.wav, generated if missing."""
    clip = ROOT / "tmp" / "test_clip.mp4"
    wav = ROOT / "tmp" / "test_beat.wav"
    if not clip.exists() or not wav.exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "make_test_media.py")],
                       check=True, cwd=ROOT)
    assert clip.exists() and wav.exists()
    return {"clip": clip, "wav": wav}
