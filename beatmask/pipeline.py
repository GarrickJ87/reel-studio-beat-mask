"""The one loop: clip + track -> tap subject -> pick effect -> beat-synced MP4.

CLI:
  python -m beatmask.pipeline --clip clip.mp4 --track song.wav --tap 540,900 --effect glow
  add --segmenter mock to run without an API key (rough GrabCut mask, not SAM).
"""
import argparse
import json
import time
from pathlib import Path

from . import beats, config, effects, media, render, segment, verify


class Project:
    """One working folder per run: tmp/work/<name>/ holding every intermediate file."""

    def __init__(self, name: str = "session", root: Path = config.WORK):
        self.dir = root / name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.clip = self.dir / "clip_1080x1920.mp4"
        self.frame0 = self.dir / "frame0.jpg"
        self.audio_wav = self.dir / "track.wav"
        self.beatmap = self.dir / "beatmap.json"
        self.masks = self.dir / "masks"
        self.sam_raw = self.dir / "sam_raw.txt"
        self.overlay = self.dir / "mask_preview.jpg"
        self.state_file = self.dir / "state.json"

    def state(self) -> dict:
        return json.loads(self.state_file.read_text()) if self.state_file.exists() else {}

    def save_state(self, **kw) -> dict:
        s = self.state()
        s.update(kw)
        self.state_file.write_text(json.dumps(s, indent=1))
        return s


def ingest(p: Project, clip_src: Path, track_src: Path, track_offset: float = 0.0) -> dict:
    info = media.normalize_clip(clip_src, p.clip)
    media.first_frame(p.clip, p.frame0)
    media.extract_audio(track_src, p.audio_wav)
    bm = beats.analyze(p.audio_wav, offset=track_offset, duration=info["duration"])
    beats.save(bm, p.beatmap)
    return p.save_state(clip_src=str(clip_src), track_src=str(track_src), track_offset=track_offset,
                        width=config.OUT_W, height=config.OUT_H, frames=info["frames"],
                        duration=info["duration"], tempo=bm["tempo"],
                        n_kicks=len(bm["kicks"]), n_snares=len(bm["snares"]), n_beats=len(bm["beats"]))


def segment_subject(p: Project, x: int, y: int, kind: str = "auto", progress=None) -> dict:
    st = p.state()
    seg = segment.get_segmenter(kind)
    res = seg.segment_video(p.clip, p.masks, x, y, st["width"], st["height"], st["frames"],
                            raw_path=p.sam_raw, progress=progress)
    render.overlay_preview(p.frame0, p.masks, p.overlay)
    return p.save_state(tap=[x, y], segmenter=res.provider, mask_frames=res.frames_with_mask,
                        segment_seconds=round(res.seconds, 1), segment_detail=res.detail)


def export(p: Project, effect: str, drive: str | None = None, out: Path | None = None,
           progress=None, verify_export: bool = True, max_retries: int = 3) -> Path:
    """Render + export. With verification on (default) the export is checked before it is returned:
    on failure it is re-rendered with stronger mask smoothing (max `max_retries` attempts), then escalated."""
    st = p.state()
    bm = json.loads(p.beatmap.read_text())
    drive = drive or effects.DEFAULT_DRIVE[effect]
    hits = beats.hits_for(bm, drive)
    out = out or p.dir / f"beatmask_{effect}_{int(time.time())}.mp4"
    report, attempts = None, (max_retries if verify_export else 1)
    for attempt in range(attempts):
        smooth = attempt  # attempt 1: raw masks, 2: vote over 2 frames, 3: vote over 3 frames
        render.render(p.clip, p.masks, Path(st["track_src"]), hits, effect, out,
                      audio_offset=st.get("track_offset", 0.0), progress=progress, smooth=smooth)
        if not verify_export:
            break
        report = verify.verify_export(p.clip, out, p.masks, hits, effect)
        report.update(attempt=attempt + 1, smoothing_frames=smooth)
        Path(str(out) + ".verify.json").write_text(json.dumps(report, indent=1))
        if report["passed"]:
            break
        print(verify.feedback(report), flush=True)
    else:
        raise verify.VerificationEscalation(report)
    p.save_state(last_export=str(out), effect=effect, drive=drive,
                 verified=bool(report and report["passed"]), signoff="pending")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clip", required=True, type=Path)
    ap.add_argument("--track", required=True, type=Path)
    ap.add_argument("--tap", required=True, help="x,y on the 1080x1920 frame (see frame0.jpg)")
    ap.add_argument("--effect", default="glow", choices=effects.EFFECTS)
    ap.add_argument("--drive", choices=["beats", "kicks", "snares", "onsets"])
    ap.add_argument("--track-offset", type=float, default=0.0, help="start the track at N seconds")
    ap.add_argument("--segmenter", default="auto", choices=["auto", "sam", "mock"])
    ap.add_argument("--name", default="cli")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    p = Project(a.name)
    say = lambda s: print(f"[beatmask] {s}", flush=True)
    say("1/4 ingest + beat map"); st = ingest(p, a.clip, a.track, a.track_offset)
    say(f"    {st['frames']} frames, {st['tempo']} BPM, {st['n_kicks']} kicks, {st['n_snares']} snares")
    x, y = (int(v) for v in a.tap.split(","))
    say("2/4 segment subject"); st = segment_subject(p, x, y, a.segmenter)
    say(f"    {st['segmenter']}: mask on {st['mask_frames']}/{st['frames']} frames in {st['segment_seconds']}s")
    say("3/4 render + 4/4 export"); out = export(p, a.effect, a.drive, a.out)
    say(f"done -> {out}")
    rep = Path(str(out) + ".verify.json")
    if rep.exists():
        r = json.loads(rep.read_text()); verify.print_report(r)
        say(f"verification {'PASSED' if r['passed'] else 'FAILED'} (attempt {r['attempt']}); sign-off PENDING: python -m beatmask.verify signoff {out}")


if __name__ == "__main__":
    main()
