"""Validate a raw OSC payload before parsing.

Errors  -> packet is unusable, drop it.
Warnings -> packet is usable but something looks off (log it).

Checks:
  - exact length == 187
  - no NaN / inf
  - packet counter advanced by 1 (warn on freeze / backwards / drop)
  - per joint: not all-zero, quaternion magnitude ~ 1
"""
from dataclasses import dataclass, field
from typing import List, Optional, Sequence
import math

from .joints import (
    EXPECTED_VALUE_COUNT,
    HEADER_LEN,
    JOINT_COUNT,
    JOINT_NAMES,
    VALUES_PER_JOINT,
)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


QUAT_MAG_TOLERANCE = 0.1
ZERO_EPSILON = 1e-6


def validate_raw_message(
    values: Sequence[float], prev_counter: Optional[int] = None
) -> ValidationResult:
    result = ValidationResult(is_valid=True)

    if len(values) != EXPECTED_VALUE_COUNT:
        result.errors.append(
            f"length mismatch: got {len(values)}, expected {EXPECTED_VALUE_COUNT}"
        )
        result.is_valid = False
        return result

    nan_idx = [i for i, v in enumerate(values) if not math.isfinite(v)]
    if nan_idx:
        preview = nan_idx[:10]
        more = "..." if len(nan_idx) > 10 else ""
        result.errors.append(f"non-finite values at indices {preview}{more}")
        result.is_valid = False
        # don't bail — still run counter check below

    counter = int(values[1]) if math.isfinite(values[1]) else -1
    if prev_counter is not None and counter >= 0:
        if counter == prev_counter:
            result.warnings.append(f"packet counter frozen at {counter}")
        elif counter < prev_counter:
            result.warnings.append(
                f"packet counter went backwards: {prev_counter} -> {counter}"
            )
        elif counter > prev_counter + 1:
            dropped = counter - prev_counter - 1
            result.warnings.append(
                f"packet counter jumped: {prev_counter} -> {counter} (dropped {dropped})"
            )

    for j in range(JOINT_COUNT):
        base = HEADER_LEN + j * VALUES_PER_JOINT
        chunk = values[base : base + VALUES_PER_JOINT]
        name = JOINT_NAMES[j]

        if all(math.isfinite(v) and abs(v) < ZERO_EPSILON for v in chunk):
            result.warnings.append(f"joint {name} is all-zero")
            continue

        qw, qx, qy, qz = chunk[3:7]
        if all(math.isfinite(v) for v in (qw, qx, qy, qz)):
            mag = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
            if abs(mag - 1.0) > QUAT_MAG_TOLERANCE:
                result.warnings.append(
                    f"joint {name} quaternion magnitude {mag:.3f} (expected ~1.0)"
                )

    return result
