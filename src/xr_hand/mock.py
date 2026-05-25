"""Mock hand-frame generator.

Produces the same 187-value list the OSC receiver will deliver, so the rest of
the pipeline (validate -> parse -> viz) is exercised exactly like production.

Fault toggles let you inject the failure modes you care about:
  - stuck_fingertip:        one tip stops moving
  - freeze_counter:         packet counter never increments
  - zero_joint:             one joint becomes all zeros
  - wrong_length:           payload truncated by one value
  - random_missing_prob:    each value has p chance of being NaN
"""
import math
import random
from typing import List, Optional

from .joints import HEADER_LEN, JOINT_NAMES


def _rest_positions() -> dict:
    """Approximate rest pose for the right hand, units in meters.

    +X = pinky direction, +Y = fingertip direction, +Z = palm-up direction.
    Mirrored for the left hand by negating X.
    """
    base_x = {"THUMB": -0.04, "INDEX": -0.025, "MIDDLE": 0.0, "RING": 0.025, "LITTLE": 0.045}
    # cumulative Y offsets for [METACARPAL, PROXIMAL, INTERMEDIATE, DISTAL, TIP]
    chains = {
        "THUMB":  [0.03, 0.07, 0.10, 0.12],                  # 4-joint chain
        "INDEX":  [0.07, 0.11, 0.135, 0.155, 0.170],
        "MIDDLE": [0.075, 0.12, 0.15, 0.172, 0.190],
        "RING":   [0.07, 0.11, 0.138, 0.158, 0.175],
        "LITTLE": [0.065, 0.095, 0.117, 0.135, 0.150],
    }
    suffixes = {
        "THUMB":  ["METACARPAL", "PROXIMAL", "DISTAL", "TIP"],
        "INDEX":  ["METACARPAL", "PROXIMAL", "INTERMEDIATE", "DISTAL", "TIP"],
        "MIDDLE": ["METACARPAL", "PROXIMAL", "INTERMEDIATE", "DISTAL", "TIP"],
        "RING":   ["METACARPAL", "PROXIMAL", "INTERMEDIATE", "DISTAL", "TIP"],
        "LITTLE": ["METACARPAL", "PROXIMAL", "INTERMEDIATE", "DISTAL", "TIP"],
    }
    pos = {"WRIST": (0.0, 0.0, 0.0), "PALM": (0.0, 0.04, 0.0)}
    for finger, ys in chains.items():
        for suffix, y in zip(suffixes[finger], ys):
            pos[f"{finger}_{suffix}"] = (base_x[finger], y, 0.0)
    return pos


_REST = _rest_positions()
_DEPTH = {"METACARPAL": 0, "PROXIMAL": 1, "INTERMEDIATE": 2, "DISTAL": 3, "TIP": 4}


class MockHandGenerator:
    def __init__(self, hand: str = "right", start_counter: int = 0):
        assert hand in ("left", "right")
        self.hand = hand
        self.counter = start_counter
        self.frame_id = 0
        self.t = 0.0
        self.dt = 1.0 / 60.0
        # Place each hand's wrist offset along X so left/right don't overlap.
        self.origin_offset = (0.12 if hand == "right" else -0.12, 0.0, 0.0)

        # fault toggles (default: clean stream)
        self.stuck_fingertip: Optional[str] = None
        self.freeze_counter: bool = False
        self.zero_joint: Optional[str] = None
        self.wrong_length: bool = False
        self.random_missing_prob: float = 0.0

        self._frozen_positions: dict = {}

    def next_frame(self) -> List[float]:
        self.t += self.dt
        if not self.freeze_counter:
            self.counter += 1
        self.frame_id += 1

        # 0..1 curl driven by a slow sine
        curl = 0.5 * (1 - math.cos(self.t * 1.5))
        side_code = 1 if self.hand == "right" else 0

        values: List[float] = [
            self.t,
            float(self.counter),
            float(side_code),
            float(self.frame_id),
            0.0,
        ]

        for name in JOINT_NAMES:
            bx, by, bz = _REST[name]
            depth = 0
            for prefix in ("THUMB", "INDEX", "MIDDLE", "RING", "LITTLE"):
                if name.startswith(prefix + "_"):
                    depth = _DEPTH.get(name.split("_", 1)[1], 0)
                    break

            # curl: deeper finger joints drop in Z and pull back in Y.
            # For the left hand, mirror the finger spread across the wrist
            # before applying the global offset (so the thumb stays on the
            # correct anatomical side).
            local_x = bx if self.hand == "right" else -bx
            x = local_x + self.origin_offset[0]
            y = by + self.origin_offset[1] - 0.015 * depth * curl
            z = bz + self.origin_offset[2] - 0.018 * depth * curl

            if self.stuck_fingertip == name:
                if name not in self._frozen_positions:
                    self._frozen_positions[name] = (x, y, z)
                x, y, z = self._frozen_positions[name]

            if self.zero_joint == name:
                values.extend([0.0] * 7)
            else:
                values.extend([x, y, z, 1.0, 0.0, 0.0, 0.0])

        if self.wrong_length:
            values.pop()

        if self.random_missing_prob > 0.0:
            for i in range(HEADER_LEN, len(values)):
                if random.random() < self.random_missing_prob:
                    values[i] = float("nan")

        return values
