"""effects.envelope: 1.0 on the hit, exponential decay after, most recent
hit wins, index -1 before the first hit."""
import math

import pytest

from beatmask import effects

HITS = [0.0, 1.0, 2.0]
DECAY = 0.18


def test_value_is_one_on_the_hit():
    for i, h in enumerate(HITS):
        env, idx = effects.envelope(h, HITS, decay=DECAY)
        assert env == 1.0, f"env at hit {h} is {env}, expected 1.0"
        assert idx == i


def test_decays_after_the_hit():
    env, _ = effects.envelope(1.0 + DECAY, HITS, decay=DECAY)
    assert env == pytest.approx(math.exp(-1.0))
    earlier, _ = effects.envelope(1.1, HITS, decay=DECAY)
    later, _ = effects.envelope(1.5, HITS, decay=DECAY)
    assert 1.0 > earlier > later > 0.0


def test_most_recent_hit_wins():
    env, idx = effects.envelope(1.6, HITS, decay=DECAY)
    assert idx == 1, f"between hits 1.0 and 2.0 the winner should be hit 1, got {idx}"
    assert env == pytest.approx(math.exp(-(1.6 - 1.0) / DECAY))


def test_index_is_minus_one_before_the_first_hit():
    env, idx = effects.envelope(-0.5, HITS, decay=DECAY)
    assert (env, idx) == (0.0, -1)
    env, idx = effects.envelope(0.0, [], decay=DECAY)
    assert (env, idx) == (0.0, -1)
