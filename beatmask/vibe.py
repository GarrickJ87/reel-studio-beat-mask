"""Stretch - Vibe: turn a text vibe ("make it aggressive") into an effect plan.

Uses Muse Spark (Meta Model API, model from config.SPARK_MODEL) over Chat
Completions with structured output. Offline tests inject a fake ``post``.
"""
import json

import requests

from . import config


class VibeError(RuntimeError):
    pass


EFFECTS = ("glow", "flash", "stutter")
DRIVES = ("kicks", "snares", "beats")

SCHEMA = {
    "type": "object",
    "properties": {
        "effect": {"type": "string", "enum": ["glow", "flash", "stutter"]},
        "drive": {"type": "string", "enum": ["kicks", "snares", "beats"]},
        "intensity": {"type": "number"},
        "why": {"type": "string"},
    },
    "required": ["effect", "drive", "intensity", "why"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You turn a text vibe into an effect plan. Reply with JSON only.\n"
    "glow = subject brightens and blooms on hits.\n"
    "flash = subject washed in color on hits.\n"
    "stutter = subject freezes with a color split on hits."
)


def _count(value) -> int:
    try:
        return len(value)
    except TypeError:
        return 0


def plan(vibe: str, beatmap: dict, post=None) -> dict:
    """Map ``vibe`` + a beat summary to an effect plan dict.

    Sends only a short summary (tempo, duration, hit counts), never the raw
    beat lists. ``post`` defaults to ``requests.post`` so tests can inject a fake.
    """
    if not isinstance(vibe, str) or not vibe.strip():
        raise VibeError("vibe is empty")
    post = post or requests.post

    tempo = beatmap.get("tempo")
    duration = beatmap.get("duration")
    n_kicks = _count(beatmap.get("kicks") or [])
    n_snares = _count(beatmap.get("snares") or [])
    n_beats = _count(beatmap.get("beats") or [])
    user_content = (
        f'Vibe: "{vibe.strip()}"\n'
        f"Track: tempo {tempo} BPM, duration {duration} s, "
        f"{n_kicks} kicks, {n_snares} snares, {n_beats} beats."
    )
    body = {
        "model": config.SPARK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "reasoning_effort": "low",
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "plan", "strict": True, "schema": SCHEMA},
        },
    }
    headers = {"Authorization": f"Bearer {config.api_key()}"}
    resp = post(f"{config.BASE_URL}/chat/completions", headers=headers, json=body, timeout=60)
    if resp.status_code != 200:
        raise VibeError(f"vibe request failed: HTTP {resp.status_code}")
    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        obj = json.loads(content)
    except Exception:
        raise VibeError("invalid vibe reply")
    effect, drive, intensity, why = obj.get("effect"), obj.get("drive"), obj.get("intensity"), obj.get("why")
    if effect not in EFFECTS:
        raise VibeError("invalid vibe reply: bad effect")
    if drive not in DRIVES:
        raise VibeError("invalid vibe reply: bad drive")
    if isinstance(intensity, bool) or not isinstance(intensity, (int, float)):
        raise VibeError("invalid vibe reply: bad intensity")
    if not isinstance(why, str):
        raise VibeError("invalid vibe reply: bad why")
    try:
        intensity = float(intensity)
    except (TypeError, ValueError):
        raise VibeError("invalid vibe reply: bad intensity")
    intensity = min(1.0, max(0.0, intensity))
    return {"effect": effect, "drive": drive, "intensity": intensity, "why": why.strip()[:200]}
