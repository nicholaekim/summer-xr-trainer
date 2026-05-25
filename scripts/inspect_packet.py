"""Capture one real-glove packet and print every value labeled.

Use this to figure out the actual layout of the 7 floats per joint, since
XR Trainer's docs are unclear. After you run it, paste the output back so
we can decide on the right interpretation.

    python scripts/inspect_packet.py
"""
import logging
import time

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

from xr_hand.joints import HEADER_LEN, JOINT_COUNT, JOINT_NAMES, VALUES_PER_JOINT

PORT = 9002
ADDRESS = "/v1/animation/kinematic/all"

logging.basicConfig(level=logging.INFO, format="%(message)s")

captured = []


def on_kinematic(address, *args):
    if not captured:
        captured.append(list(args))


def main():
    d = Dispatcher()
    d.map(ADDRESS, on_kinematic)
    d.set_default_handler(lambda *_: None)
    server = ThreadingOSCUDPServer(("0.0.0.0", PORT), d)
    print(f"Listening on {PORT} {ADDRESS} — move the glove for one packet...")
    import threading
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    timeout = 10.0
    t0 = time.time()
    while not captured and time.time() - t0 < timeout:
        time.sleep(0.05)
    server.shutdown(); server.server_close()

    if not captured:
        print("no packet received in 10s — is XR Trainer streaming?")
        return

    args = captured[0]
    print(f"\nGot 1 packet, {len(args)} args\n")

    print("=== HEADER (5 values) ===")
    for i in range(HEADER_LEN):
        v = args[i]
        type_name = type(v).__name__
        print(f"  [{i}] {type_name:6s} = {v!r}")

    print("\n=== JOINTS (26 x 7 = 182 values) ===")
    print(f"  {'name':<22} {'v0':>10} {'v1':>10} {'v2':>10} {'v3':>10} {'v4':>10} {'v5':>10} {'v6':>10}")
    for j in range(JOINT_COUNT):
        base = HEADER_LEN + j * VALUES_PER_JOINT
        chunk = args[base : base + VALUES_PER_JOINT]
        vals_str = "  ".join(f"{v:>+8.4f}" if isinstance(v, (int, float)) else f"{str(v):>10}" for v in chunk)
        print(f"  {JOINT_NAMES[j]:<22} {vals_str}")

    print("\n=== COLUMN STATS (across 26 joints, helps spot which cols are positions vs quaternions) ===")
    print(f"  {'col':>4}  {'min':>10}  {'max':>10}  {'mean':>10}  {'abs_max':>10}")
    for col in range(VALUES_PER_JOINT):
        vals = [args[HEADER_LEN + j * VALUES_PER_JOINT + col] for j in range(JOINT_COUNT)]
        vals = [v for v in vals if isinstance(v, (int, float))]
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        mean = sum(vals) / len(vals)
        absmax = max(abs(v) for v in vals)
        print(f"  v{col}    {lo:>+10.4f}  {hi:>+10.4f}  {mean:>+10.4f}  {absmax:>+10.4f}")

    print("\n=== Plausible quaternion check ===")
    print("If 4 of the columns hover near magnitude 1 across joints, those are the quaternion.")
    for a, b, c, dd in [(0,1,2,3), (3,4,5,6)]:
        mags = []
        for j in range(JOINT_COUNT):
            base = HEADER_LEN + j * VALUES_PER_JOINT
            qs = [args[base + k] for k in (a, b, c, dd)]
            if all(isinstance(q, (int, float)) for q in qs):
                mags.append(sum(q * q for q in qs) ** 0.5)
        if mags:
            avg = sum(mags) / len(mags)
            print(f"  cols [{a},{b},{c},{dd}] -> avg magnitude {avg:.3f}, range [{min(mags):.3f}, {max(mags):.3f}]")


if __name__ == "__main__":
    main()
