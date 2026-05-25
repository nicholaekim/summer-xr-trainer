"""Throwaway smoke test: in-process OSC loop with mock sender.

Not part of the user-facing flow. Delete or keep as a quick CI check.
"""
import logging
import threading
import time

from pythonosc.udp_client import SimpleUDPClient

from xr_hand.mock import MockHandGenerator
from xr_hand.parser import parse_hand_message
from xr_hand.receiver import OSCHandReceiver
from xr_hand.validator import validate_raw_message

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")

PORT = 9123
DURATION = 2.0

rx = OSCHandReceiver(host="127.0.0.1", port=PORT)
rx.start()

stop = threading.Event()


def sender():
    c = SimpleUDPClient("127.0.0.1", PORT)
    left = MockHandGenerator(hand="left")
    right = MockHandGenerator(hand="right")
    while not stop.is_set():
        c.send_message("/hand/left", left.next_frame())
        c.send_message("/hand/right", right.next_frame())
        time.sleep(1 / 60)


threading.Thread(target=sender, daemon=True).start()

prev = {"left": None, "right": None}
valid = {"left": 0, "right": 0}
warns = {"left": 0, "right": 0}
errs = {"left": 0, "right": 0}

t0 = time.time()
while time.time() - t0 < DURATION:
    for hand, raw in rx.drain(64):
        res = validate_raw_message(raw, prev[hand])
        if not res.is_valid:
            errs[hand] += 1
            continue
        warns[hand] += len(res.warnings)
        f = parse_hand_message(raw, hand_side_hint=hand)
        prev[hand] = f.packet_counter
        valid[hand] += 1
    time.sleep(0.005)

stop.set()
rx.stop()

print(f"received:  {rx.msg_count}  dropped: {rx.dropped}")
print(f"validated: {valid}")
print(f"warnings:  {warns}")
print(f"errors:    {errs}")
print(f"last_counters: {prev}")
