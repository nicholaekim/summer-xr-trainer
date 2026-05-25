"""Listen on many UDP ports at once and report which one is receiving OSC.

Use when a sender (e.g. XR Trainer beta) doesn't expose a "destination port"
setting and you need to discover what port it's actually using.

    python scripts/osc_scanner.py
    python scripts/osc_scanner.py --ports 9000 9001 8000   # custom list
"""
import argparse
import logging
import threading
import time

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scan")

# Common OSC / motion-capture / StretchSense ports.
DEFAULT_PORTS = [
    5000, 5001, 5005, 5006, 5103, 5555,
    7000, 7001, 7400, 7401, 7770,
    8000, 8001, 8080, 8888,
    9000, 9001, 9002, 9090, 9999,
    10000, 10001, 12345, 38001, 57121,
]


def make_handler(port: int):
    def handler(address, *args):
        if args:
            preview = ", ".join(
                f"{a:.3f}" if isinstance(a, float) else str(a)[:20]
                for a in args[:5]
            )
        else:
            preview = "(no args)"
        log.info(
            "[port %5d] %s  args=%d  first5=[%s]",
            port, address, len(args), preview,
        )
    return handler


def serve(port: int):
    d = Dispatcher()
    d.set_default_handler(make_handler(port))
    try:
        server = ThreadingOSCUDPServer(("0.0.0.0", port), d)
    except OSError as e:
        log.warning("[port %5d] cannot bind: %s", port, e)
        return
    log.info("[port %5d] listening", port)
    server.serve_forever()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ports", nargs="*", type=int, default=DEFAULT_PORTS)
    args = p.parse_args()

    for port in args.ports:
        threading.Thread(target=serve, args=(port,), daemon=True).start()

    log.info(
        "scanning %d ports. move the gloves around. Ctrl+C to stop.",
        len(args.ports),
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("done")


if __name__ == "__main__":
    main()
