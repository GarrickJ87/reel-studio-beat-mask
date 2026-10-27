"""beats.analyze on the synthetic 120 BPM loop: 8 kicks on whole seconds,
8 snares on half seconds, each within +-30 ms."""
from beatmask import beats

TOL = 0.030


def test_kicks_on_whole_seconds(test_media):
    bm = beats.analyze(test_media["wav"])
    assert len(bm["kicks"]) == 8, f"expected 8 kicks, got {bm['kicks']}"
    for got, want in zip(bm["kicks"], range(8)):
        assert abs(got - want) <= TOL, f"kick at {got}, expected {want} +- {TOL}"


def test_snares_on_half_seconds(test_media):
    bm = beats.analyze(test_media["wav"])
    assert len(bm["snares"]) == 8, f"expected 8 snares, got {bm['snares']}"
    for got, want in zip(bm["snares"], [0.5 + i for i in range(8)]):
        assert abs(got - want) <= TOL, f"snare at {got}, expected {want} +- {TOL}"
