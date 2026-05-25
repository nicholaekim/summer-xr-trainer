"""Send mock hand frames over OSC so you can test the receiver without gloves.

Run this in one terminal, then in a second terminal run `run_osc.py`. The
sender plays the role of XR Trainer; the receiver behaves identically to how
it will when real gloves are connected.

Usage:
    python scripts/mock_osc_sender.py                          # 60 Hz, both hands
    python scripts/mock_osc_sender.py --rate 90
    python scripts/mock_osc_sender.py --fault stuck_fingertip  # inject a fault
"""
import argparse
import logging
import time

from pythonosc.udp_client import SimpleUDPClient

from xr_hand.mock import MockHandGenerator


FAULTS = {
    "none": lambda g: None,
    "stuck_fingertip": lambda g: setattr(g, "stuck_fingertip", "INDEX_TIP"),
    "freeze_counter": lambda g: setattr(g, "freeze_counter", True),
    "zero_joint": lambda g: setattr(g, "zero_joint", "MIDDLE_PROXIMAL"),
    "wrong_length": lambda g: setattr(g, "wrong_length", True),
    "random_missing": lambda g: setattr(g, "random_missing_prob", 0.01),
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--left-addr", default="/hand/left")
    p.add_argument("--right-addr", default="/hand/right")
    p.add_argument("--rate", type=float, default=60.0,
                   help="Frames per second per hand.")
    p.add_argument("--fault", choices=sorted(FAULTS), default="none",
                   help="Inject a fault on the RIGHT hand only.")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("sender")

    client = SimpleUDPClient(args.host, args.port)
    left = MockHandGenerator(hand="left")
    right = MockHandGenerator(hand="right")
    FAULTS[args.fault](right)
    period = 1.0 / args.rate

    log.info(
        "sending to %s:%d at %.1f Hz (fault=%s)",
        args.host, args.port, args.rate, args.fault,
    )
    sent = 0
    try:
        while True:
            t0 = time.time()
            client.send_message(args.left_addr, left.next_frame())
            client.send_message(args.right_addr, right.next_frame())
            sent += 2
            if sent % 240 == 0:
                log.info("sent=%d", sent)
            elapsed = time.time() - t0
            sleep_for = period - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
    except KeyboardInterrupt:
        log.info("stopped; sent=%d", sent)


if __name__ == "__main__":
    main()
