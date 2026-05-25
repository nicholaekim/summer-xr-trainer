"""Headless fault-injection verification.

For each fault toggle, runs the mock generator through the validator for N
frames and prints the first error/warning produced. Lets you confirm the
pipeline reacts to bad data without launching the GUI.
"""
from typing import Callable, Optional

from xr_hand.mock import MockHandGenerator
from xr_hand.validator import validate_raw_message

FRAMES = 60


def run_case(
    name: str,
    configure: Callable[[MockHandGenerator], None],
    look_for: str,
    in_errors: bool = False,
) -> bool:
    gen = MockHandGenerator(hand="right")
    configure(gen)
    prev: Optional[int] = None
    saw = None
    for _ in range(FRAMES):
        raw = gen.next_frame()
        r = validate_raw_message(raw, prev)
        # When length is wrong values[1] is still readable, but for total
        # safety just guard the indexing.
        try:
            prev = int(raw[1])
        except (IndexError, ValueError):
            pass
        pool = r.errors if in_errors else r.warnings
        for msg in pool:
            if look_for in msg:
                saw = msg
                break
        if saw:
            break
    ok = saw is not None
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")
    print(f"         expected {'error' if in_errors else 'warning'} containing: {look_for!r}")
    print(f"         got:      {saw!r}")
    return ok


cases = [
    (
        "clean stream (control)",
        lambda g: None,
        None,  # we check this one specially
        False,
    ),
    (
        "stuck_fingertip",
        lambda g: setattr(g, "stuck_fingertip", "INDEX_TIP"),
        # No log expected for stuck fingertip — that's a visual-only fault.
        # We still want the stream to remain valid.
        None,
        False,
    ),
    (
        "freeze_counter",
        lambda g: setattr(g, "freeze_counter", True),
        "frozen",
        False,
    ),
    (
        "zero_joint",
        lambda g: setattr(g, "zero_joint", "MIDDLE_PROXIMAL"),
        "MIDDLE_PROXIMAL",
        False,
    ),
    (
        "wrong_length",
        lambda g: setattr(g, "wrong_length", True),
        "length mismatch",
        True,
    ),
    (
        "random_missing_prob",
        lambda g: setattr(g, "random_missing_prob", 0.01),
        "non-finite",
        True,
    ),
]


def check_clean_stream() -> bool:
    gen = MockHandGenerator(hand="right")
    prev: Optional[int] = None
    for _ in range(FRAMES):
        raw = gen.next_frame()
        r = validate_raw_message(raw, prev)
        if not r.is_valid or r.warnings:
            print(f"[FAIL] clean stream: unexpected validation noise: "
                  f"errors={r.errors} warnings={r.warnings}")
            return False
        prev = int(raw[1])
    print("[PASS] clean stream (control)")
    print("         no errors, no warnings over 60 frames")
    return True


def check_stuck_fingertip_stays_valid() -> bool:
    gen = MockHandGenerator(hand="right")
    gen.stuck_fingertip = "INDEX_TIP"
    prev: Optional[int] = None
    for _ in range(FRAMES):
        raw = gen.next_frame()
        r = validate_raw_message(raw, prev)
        if not r.is_valid:
            print(f"[FAIL] stuck_fingertip: stream went invalid: {r.errors}")
            return False
        prev = int(raw[1])
    print("[PASS] stuck_fingertip (visual-only — stream stays valid)")
    print("         no errors raised; verify visually in viewer")
    return True


if __name__ == "__main__":
    results = []
    results.append(check_clean_stream())
    print()
    results.append(check_stuck_fingertip_stays_valid())
    print()
    for name, cfg, needle, in_err in cases[2:]:
        results.append(run_case(name, cfg, needle, in_err))
        print()
    print("=" * 50)
    print(f"  {sum(results)}/{len(results)} checks passed")
