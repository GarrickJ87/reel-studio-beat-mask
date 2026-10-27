"""Pipeline end to end with the mock segmenter on the synthetic media:
MP4 exists, is 1080x1920, has audio. No network, no API key."""
from beatmask import media, pipeline


def test_pipeline_mock_end_to_end(test_media):
    p = pipeline.Project("pytest-e2e")
    st = pipeline.ingest(p, test_media["clip"], test_media["wav"])
    assert st["frames"] > 0
    st = pipeline.segment_subject(p, 540, 960, kind="mock")
    assert st["mask_frames"] > 0, "mock segmenter found the subject on no frames"
    out = p.dir / "pytest_glow.mp4"
    if out.exists():
        out.unlink()
    pipeline.export(p, "glow", out=out)
    assert out.exists(), f"no export at {out}"
    assert out.stat().st_size > 0
    info = media.probe(out)
    assert (info["width"], info["height"]) == (1080, 1920), info
    assert info["has_audio"] is True, info
