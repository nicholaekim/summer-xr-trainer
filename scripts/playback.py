"""Replay a JSONL recording through the 3D viewer.

Usage:
    python scripts/playback.py recordings/20260525_143000.jsonl
    python scripts/playback.py recording.jsonl --rate 0.5   # half speed
    python scripts/playback.py recording.jsonl --loop
"""
import argparse
import logging
import time
from pathlib import Path

from xr_hand.recorder import FrameRecorder
from xr_hand.viz3d import HandViewer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("playback")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path, help="Path to .jsonl recording.")
    p.add_argument("--rate", type=float, default=1.0,
                   help="Playback speed multiplier (1.0 = real time, 0.5 = half speed).")
    p.add_argument("--loop", action="store_true", help="Loop the recording indefinitely.")
    args = p.parse_args()

    if not args.input.exists():
        raise SystemExit(f"file not found: {args.input}")

    # Load all frames up front so we know the total count and can loop.
    frames_with_time = list(FrameRecorder.load(args.input))
    if not frames_with_time:
        raise SystemExit("recording is empty")

    log.info("loaded %d frames from %s", len(frames_with_time), args.input)

    viewer = HandViewer(title=f"Playback: {args.input.name}")
    queue = []  # frames ready to draw this tick

    def load_pass() -> list:
        """Build a timed list for one playback pass."""
        result = []
        if not frames_with_time:
            return result
        t0_wall = frames_with_time[0][1]  # wall_time of first recorded frame
        play_start = time.time()
        for frame, wall_time in frames_with_time:
            relative = (wall_time - t0_wall) / args.rate
            result.append((play_start + relative, frame))
        return result

    pending = load_pass()
    frame_idx = [0]

    def tick() -> None:
        now = time.time()
        # Emit every frame whose scheduled time has arrived.
        while frame_idx[0] < len(pending) and pending[frame_idx[0]][0] <= now:
            _, frame = pending[frame_idx[0]]
            viewer.update_hand(frame)
            frame_idx[0] += 1

        if frame_idx[0] >= len(pending):
            if args.loop:
                log.info("looping")
                pending.clear()
                pending.extend(load_pass())
                frame_idx[0] = 0
            else:
                log.info("playback complete (%d frames)", len(frames_with_time))

    viewer.run(tick, interval_ms=16)


if __name__ == "__main__":
    main()
