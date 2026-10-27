"""segment.parse_records and segment.mask_to_frame, offline.

The sample wire line below is real SAM 3.1 output captured from the live API
(tmp/sam_smoke_raw.txt, Oct 27 2026), embedded so the tests don't depend on
gitignored scratch files. Its box is x 269..451, y 460..793 in a 720x1280 frame.
The two-record sample follows the per-line grammar in docs/META-MODELS.md.
"""
import dataclasses

import pytest

from beatmask import segment

# One real SAM 3.1 wire line, object id 1, frame 0.
SAMPLE_LINE = ("<0f>1<|box;x1=269;y1=460;x2=450;y2=792;w=720;h=1280|>"
               "<|mask;x=0;y=0;data=333,182,!!!!!uGNl#*x6`hnGY4JA5bFy&cSg:.o:{N#-3o]_Pp/#6hYd5s0?)"
               "witI{.^EfXga0MtzG7oTQ@0?eXPXM0%YkUroMn&H#]#Bhe{!!!|>")


def test_parse_records_two_objects():
    line0 = SAMPLE_LINE.replace("<0f>1<|", "<0f>0<|", 1)
    masks, _ = segment.parse_records(line0 + "\n" + SAMPLE_LINE)
    assert len(masks) == 2, f"expected 2 records, got {len(masks)}"
    assert [m.object_id for m in masks] == ["0", "1"]


def test_mask_to_frame_clips_box_off_right_and_bottom():
    rec = segment.parse_records(SAMPLE_LINE)[0][0]
    clipped = segment.mask_to_frame(rec, 400, 600)   # box runs past x=400 and y=600
    full = segment.mask_to_frame(rec, 720, 1280)
    assert clipped.shape == (600, 400)
    assert clipped.dtype.name == "uint8"
    assert set(clipped.reshape(-1).tolist()) <= {0, 255}
    assert (clipped == full[:600, :400]).all(), "clipped paste must equal the cropped full paste"


def test_mask_to_frame_clips_box_off_left_and_top():
    rec = segment.parse_records(SAMPLE_LINE)[0][0]
    shifted = dataclasses.replace(rec, bounds=dataclasses.replace(
        rec.bounds, left=-50, right=132, top=-30, bottom=303))
    out = segment.mask_to_frame(shifted, 400, 600)
    assert out.shape == (600, 400)
    assert out.any(), "the visible part of the box should still paste something"


@pytest.mark.xfail(strict=True, reason="box fully outside the frame crashes the paste "
        "(ValueError: could not broadcast); reported to Claude Code, not fixed on this branch")
def test_mask_to_frame_box_fully_outside_frame():
    rec = segment.parse_records(SAMPLE_LINE)[0][0]
    outside = dataclasses.replace(rec, bounds=dataclasses.replace(
        rec.bounds, left=469, right=651, top=660, bottom=993))
    out = segment.mask_to_frame(outside, 300, 500)
    assert out.shape == (500, 300)
    assert not out.any()
