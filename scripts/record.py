"""Record validated hand frames to a JSONL file.

Mock mode (no hardware):
    python scripts/record.py --mock --duration 10

Live OSC mode (XR Trainer connected):
    python scripts/record.py --port 9000

Recordings land in recordings/ by default.
"""
import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

from xr_hand.mock import MockHandGenerator
from xr_hand.parser import parse_hand_message
from xr_hand.receiver import OSCHandReceiver
from xr_hand.recorder import FrameRecorder
from xr_hand.validator import StreamMonitor, validate_raw_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("record")


def default_output() -> Path:
    return Path("recordings") / f"{datetime.now():%Y%m%d_%H%M%S}.jsonl"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true", help="Use mock generator instead of OSC.")
    p.add_argument("--port", type=int, default=9002)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--address", default="/v1/animation/kinematic/all")
    p.add_argument("--left-addr", default="/hand/left")
    p.add_argument("--right-addr", default="/hand/right")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--duration", type=float, default=None,
                   help="Stop after this many seconds (default: run until Ctrl+C).")
    args = p.parse_args()

    output = args.output or default_output()
    recorder = FrameRecorder()
    recorder.start(output)
    log.info("recording to %s", output)

    monitors = {"left": StreamMonitor("left"), "right": StreamMonitor("right")}

    def handle(hand: str, raw: list) -> None:
        result = validate_raw_message(raw)
        if not result.is_valid:
            log.warning("[%s] INVALID (skipped): %s", hand, "; ".join(result.errors))
            return
        for w in result.warnings:
            log.warning("[%s] %s", hand, w)
        frame = parse_hand_message(raw, hand_side_hint=hand)
        for w in monitors[hand].update(frame.packet_counter):
            log.warning("[%s] %s", hand, w)
        recorder.record(frame)

    try:
        if args.mock:
            left = MockHandGenerator(hand="left")
            right = MockHandGenerator(hand="right")
            period = 1.0 / 60.0
            deadline = time.time() + args.duration if args.duration else None
            log.info("mock mode (Ctrl+C or --duration to stop)")
            while True:
                if deadline and time.time() >= deadline:
                    break
                t0 = time.time()
                handle("left", left.next_frame())
                handle("right", right.next_frame())
                if recorder.count % 120 == 0:
                    log.info("frames recorded: %d", recorder.count)
                elapsed = time.time() - t0
                time.sleep(max(0.0, period - elapsed))
        else:
            rx = OSCHandReceiver(
                host=args.host, port=args.port,
                kinematic_addr=args.address,
                left_addr=args.left_addr, right_addr=args.right_addr,
            )
            rx.start()
            deadline = time.time() + args.duration if args.duration else None
            log.info("OSC mode on %s:%d (Ctrl+C to stop)", args.host, args.port)
            while True:
                if deadline and time.time() >= deadline:
                    break
                for hand, raw in rx.drain(64):
                    handle(hand, raw)
                if recorder.count % 120 == 0 and recorder.count > 0:
                    log.info("frames recorded: %d", recorder.count)
                time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        recorder.stop()
        log.info("saved %d frames to %s", recorder.count, output)


if __name__ == "__main__":
    main()
