"""Tempo: the 120 BPM synthetic loop must not be read as 80.75 BPM, and beats must land on 0, 0.5, 1.0 ... s."""
import numpy as np

from beatmask import beats

TOL = 0.030


def test_tempo_is_120_on_the_synthetic_loop(test_media):
    bm = beats.analyze(test_media["wav"])
    assert abs(bm["tempo"] - 120) < 2, bm["tempo"]


def test_beats_land_on_half_seconds(test_media):
    bm = beats.analyze(test_media["wav"])
    for t in bm["beats"]:
        nearest = round(t / 0.5) * 0.5
        assert abs(t - nearest) <= TOL, f"beat at {t}, nearest half second {nearest}"
    assert len(bm["beats"]) >= 14, bm["beats"]


def test_grid_from_hits_rejects_irregular_hits():
    assert beats.grid_from_hits([0.0, 0.37, 1.1, 1.15, 2.9], 4.0) is None
