"""Round-trip tests for FrameRecorder."""
import tempfile
from pathlib import Path

from xr_hand.mock import MockHandGenerator
from xr_hand.parser import parse_hand_message
from xr_hand.recorder import FrameRecorder
from xr_hand.validator import validate_raw_message


def _make_frames(hand: str, n: int):
    gen = MockHandGenerator(hand=hand)
    frames = []
    prev = None
    for _ in range(n):
        raw = gen.next_frame()
        assert validate_raw_message(raw, prev).is_valid
        frame = parse_hand_message(raw, hand_side_hint=hand)
        prev = frame.packet_counter
        frames.append(frame)
    return frames


def test_round_trip():
    original = _make_frames("right", 30)
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = Path(f.name)

    rec = FrameRecorder()
    rec.start(path)
    for frame in original:
        rec.record(frame)
    rec.stop()
    assert rec.count == 30

    loaded = [frame for frame, _ in FrameRecorder.load(path)]
    assert len(loaded) == 30
    assert loaded[0].hand_side == "right"
    assert loaded[0].joints[0].name == "PALM"
    assert loaded[-1].packet_counter == original[-1].packet_counter

    for orig, back in zip(original, loaded):
        assert orig.packet_counter == back.packet_counter
        assert orig.hand_side == back.hand_side
        for jo, jb in zip(orig.joints, back.joints):
            assert jo.name == jb.name
            assert abs(jo.x - jb.x) < 1e-9


def test_both_hands_interleaved():
    left_frames = _make_frames("left", 10)
    right_frames = _make_frames("right", 10)

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = Path(f.name)

    rec = FrameRecorder()
    rec.start(path)
    for l, r in zip(left_frames, right_frames):
        rec.record(l)
        rec.record(r)
    rec.stop()
    assert rec.count == 20

    loaded = [frame for frame, _ in FrameRecorder.load(path)]
    sides = [f.hand_side for f in loaded]
    assert sides[::2] == ["left"] * 10
    assert sides[1::2] == ["right"] * 10


def test_wall_times_are_monotonic():
    frames = _make_frames("right", 20)
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = Path(f.name)

    rec = FrameRecorder()
    rec.start(path)
    for frame in frames:
        rec.record(frame)
    rec.stop()

    wall_times = [wt for _, wt in FrameRecorder.load(path)]
    assert all(b >= a for a, b in zip(wall_times, wall_times[1:]))
