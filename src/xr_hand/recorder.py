"""Save and load validated hand frames as JSONL.

One JSON object per line — easy to inspect in a text editor, grep for
specific joints, or send to a professor / StretchSense support.

Format of each line:
{
  "wall_time": 1748123456.789,    # real clock time (for replay timing)
  "timestamp": 4.233,             # OSC packet timestamp
  "packet_counter": 254,
  "hand_side": "right",
  "frame_id": 254,
  "status": 0,
  "joints": [
    {"name": "PALM", "x": 0.0, "y": 0.04, "z": 0.0,
     "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0},
    ...
  ]
}
"""
import json
import time
from pathlib import Path
from typing import Generator, Optional

from .joints import HandFrame, Joint


def _frame_to_dict(frame: HandFrame, wall_time: float) -> dict:
    return {
        "wall_time": wall_time,
        "timestamp": frame.timestamp,
        "packet_counter": frame.packet_counter,
        "hand_side": frame.hand_side,
        "frame_id": frame.frame_id,
        "status": frame.status,
        "joints": [
            {
                "name": j.name,
                "x": j.x, "y": j.y, "z": j.z,
                "qw": j.qw, "qx": j.qx, "qy": j.qy, "qz": j.qz,
            }
            for j in frame.joints
        ],
    }


def _dict_to_frame(d: dict) -> tuple[HandFrame, float]:
    joints = [
        Joint(
            name=j["name"],
            x=j["x"], y=j["y"], z=j["z"],
            qw=j["qw"], qx=j["qx"], qy=j["qy"], qz=j["qz"],
        )
        for j in d["joints"]
    ]
    frame = HandFrame(
        timestamp=d["timestamp"],
        packet_counter=d["packet_counter"],
        hand_side=d["hand_side"],
        frame_id=d["frame_id"],
        status=d["status"],
        joints=joints,
    )
    return frame, d["wall_time"]


class FrameRecorder:
    def __init__(self, hz: Optional[float] = None):
        """hz: downsample to this many frames/sec (e.g. 5.0). None = keep all."""
        self._file = None
        self.path: Optional[Path] = None
        self.count = 0
        self._interval = 1.0 / hz if hz else None
        self._next_sample: dict[str, float] = {}

    def start(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "w", encoding="utf-8")
        self.count = 0
        self._next_sample = {}

    def record(self, frame: HandFrame) -> None:
        if self._file is None:
            raise RuntimeError("call start() before record()")
        now = time.time()
        if self._interval is not None:
            # throttle each hand independently so both keep the full target rate
            if now < self._next_sample.get(frame.hand_side, 0.0):
                return  # too soon — drop this frame to hold the target rate
            # schedule next sample from this write; avoids a burst after a gap
            self._next_sample[frame.hand_side] = now + self._interval
        d = _frame_to_dict(frame, wall_time=now)
        self._file.write(json.dumps(d) + "\n")
        self._file.flush()
        self.count += 1

    def stop(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    @staticmethod
    def load(path: str | Path) -> Generator[tuple[HandFrame, float], None, None]:
        """Yield (HandFrame, wall_time) for each recorded frame."""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield _dict_to_frame(json.loads(line))
