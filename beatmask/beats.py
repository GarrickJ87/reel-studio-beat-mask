"""Stage 3 - Beat map: beats, kicks and snares from the track. Plain DSP (librosa), no AI.

Kicks = onsets in the low band (<150 Hz). Snares = onsets in the 1.5-6 kHz band.
Output is a list of hit times in seconds, which the renderer turns into effect envelopes.
"""
import json
from pathlib import Path

import librosa
import numpy as np

HOP = 512


def _band_onsets(y, sr, fmin, fmax, threshold):
    """Spectral flux of one frequency band, peak-picked. threshold = fraction of the loudest hit."""
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    energy = S[(freqs >= fmin) & (freqs < fmax)].sum(axis=0)
    loud = np.sqrt(energy)  # amplitude, so quiet bleed from other drums stays small
    env = np.maximum(0.0, np.diff(loud, prepend=0.0))
    if env.max() > 0:
        env = env / env.max()
    min_gap = max(1, int(0.09 * sr / HOP))  # ~90 ms between hits of the same drum
    frames = librosa.util.peak_pick(env, pre_max=3, post_max=3, pre_avg=10, post_avg=3,
                                    delta=threshold, wait=min_gap)
    times = librosa.frames_to_time(frames, sr=sr, hop_length=HOP)
    strength = env[frames] if len(frames) else np.array([])
    return times, strength


def analyze(audio_path: Path, offset: float = 0.0, duration: float | None = None) -> dict:
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True, offset=offset, duration=duration)
    if len(y) == 0:
        raise ValueError("track is empty or offset is past its end")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP)
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=HOP)
    onsets = librosa.frames_to_time(onset_frames, sr=sr, hop_length=HOP)
    kicks, kick_str = _band_onsets(y, sr, 20, 150, threshold=0.25)
    snares, snare_str = _band_onsets(y, sr, 1500, 6000, threshold=0.25)
    r = lambda a: [round(float(t), 4) for t in a]
    return {
        "tempo": round(float(np.atleast_1d(tempo)[0]), 2),
        "duration": round(len(y) / sr, 3),
        "beats": r(beats),
        "onsets": r(onsets),
        "kicks": r(kicks),
        "kick_strength": r(kick_str),
        "snares": r(snares),
        "snare_strength": r(snare_str),
    }


def save(beatmap: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(beatmap, indent=1))
    return path


def hits_for(beatmap: dict, drive: str) -> list[float]:
    """drive = beats | kicks | snares | onsets. Falls back to beats when a band found nothing."""
    hits = beatmap.get(drive) or []
    return hits if hits else beatmap.get("beats", [])
