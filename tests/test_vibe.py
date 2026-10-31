"""Offline tests for beatmask/vibe.py. Fake post, no network, no API key."""
import json

import pytest

from beatmask import config, vibe
from beatmask.vibe import VibeError, plan

BEATMAP = {
    "tempo": 120.0,
    "duration": 10.0,
    "kicks": [0.5, 1.0, 1.5],
    "snares": [1.0, 2.0],
    "beats": [0.0, 0.5, 1.0, 1.5, 2.0],
}


class FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def fake_post_factory(content_obj=None, status_code=200, raw_content=None, capture=None):
    def fake_post(url, headers=None, json=None, timeout=None):
        if capture is not None:
            capture["url"] = url
            capture["headers"] = headers
            capture["json"] = json
            capture["timeout"] = timeout
        if status_code != 200:
            return FakeResp(status_code=status_code, payload={})
        text = raw_content if raw_content is not None else json_module_dumps(content_obj)
        return FakeResp(status_code=200, payload={"choices": [{"message": {"content": text}}]})

    return fake_post


def json_module_dumps(obj):
    return json.dumps(obj)


def test_valid_reply_parsed():
    post = fake_post_factory({"effect": "flash", "drive": "kicks", "intensity": 0.8, "why": "hits hard"})
    out = plan("make it aggressive", BEATMAP, post=post)
    assert out["effect"] == "flash"
    assert out["drive"] == "kicks"
    assert isinstance(out["intensity"], float) and out["intensity"] == pytest.approx(0.8)
    assert isinstance(out["why"], str) and out["why"] == "hits hard"


def test_intensity_clamped():
    hi = plan("x", BEATMAP, post=fake_post_factory(
        {"effect": "glow", "drive": "beats", "intensity": 1.7, "why": "y"}))
    assert hi["intensity"] == 1.0
    lo = plan("x", BEATMAP, post=fake_post_factory(
        {"effect": "glow", "drive": "beats", "intensity": -0.2, "why": "y"}))
    assert lo["intensity"] == 0.0


def test_bad_effect_raises():
    post = fake_post_factory({"effect": "explode", "drive": "kicks", "intensity": 0.5, "why": "y"})
    with pytest.raises(VibeError):
        plan("aggressive", BEATMAP, post=post)


def test_non_200_raises_without_leaking_key():
    def post(url, headers=None, json=None, timeout=None):
        return FakeResp(status_code=500, payload={"error": "boom"})

    with pytest.raises(VibeError) as exc:
        plan("aggressive", BEATMAP, post=post)
    auth = f"Bearer {config.api_key()}"
    assert auth not in str(exc.value)


def test_request_body_shape_and_summary():
    capture = {}
    post = fake_post_factory(
        {"effect": "stutter", "drive": "snares", "intensity": 0.4, "why": "ok"}, capture=capture)
    plan("moody", BEATMAP, post=post)
    body = capture["json"]
    assert body["model"] == "muse-spark-1.3" == config.SPARK_MODEL
    assert body["reasoning_effort"] == "low"
    assert body["response_format"]["type"] == "json_schema"
    texts = [m["content"] for m in body["messages"]]
    user_text = next(t for m, t in zip(body["messages"], texts) if m["role"] == "user")
    assert "120" in user_text  # tempo
    assert "3" in user_text and "2" in user_text and "5" in user_text  # kick/snare/beat counts
    for t in texts:
        for hit in ["0.5", "1.5"]:
            # raw beat times must not leak; counts only
            assert hit not in t
    assert capture["timeout"] == 60


def test_empty_vibe_never_calls_api():
    called = []

    def post(url, headers=None, json=None, timeout=None):
        called.append(url)
        return FakeResp(status_code=200, payload={})

    with pytest.raises(VibeError):
        plan("   ", BEATMAP, post=post)
    assert called == []
