"""Parse a raw 187-value OSC payload into a HandFrame.

Header layout assumed (until confirmed against real Open SDK stream):
    [0] timestamp (seconds, float)
    [1] packet counter (int)
    [2] hand side code (0 = left, 1 = right)
    [3] frame id (int)
    [4] status flag (int)
Followed by 26 joints x [x, y, z, qw, qx, qy, qz].
"""
from typing import Optional, Sequence

from .joints import (
    EXPECTED_VALUE_COUNT,
    HEADER_LEN,
    JOINT_COUNT,
    JOINT_NAMES,
    VALUES_PER_JOINT,
    HandFrame,
    Joint,
)


class PacketParseError(ValueError):
    pass


def parse_hand_message(
    values: Sequence[float], hand_side_hint: Optional[str] = None
) -> HandFrame:
    if len(values) != EXPECTED_VALUE_COUNT:
        raise PacketParseError(
            f"expected {EXPECTED_VALUE_COUNT} values, got {len(values)}"
        )

    timestamp = float(values[0])
    packet_counter = int(values[1])
    side_code = int(values[2])
    frame_id = int(values[3])
    status = int(values[4])
    hand_side = hand_side_hint or ("right" if side_code == 1 else "left")

    joints = []
    for j in range(JOINT_COUNT):
        base = HEADER_LEN + j * VALUES_PER_JOINT
        x, y, z, qw, qx, qy, qz = values[base : base + VALUES_PER_JOINT]
        joints.append(
            Joint(
                name=JOINT_NAMES[j],
                x=float(x), y=float(y), z=float(z),
                qw=float(qw), qx=float(qx), qy=float(qy), qz=float(qz),
            )
        )

    return HandFrame(
        timestamp=timestamp,
        packet_counter=packet_counter,
        hand_side=hand_side,
        frame_id=frame_id,
        status=status,
        joints=joints,
    )
