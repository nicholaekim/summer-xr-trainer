"""Interactive 3D skeletal viewer.

Built on matplotlib's mplot3d for zero install pain on Windows. Click-and-drag
rotates the view, scroll zooms. The HandViewer class is the only surface the
rest of the pipeline touches, so you can later swap matplotlib for pyvista /
open3d / a Unity bridge without changing scripts.
"""
from typing import Callable, Dict, Optional

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d.art3d import Line3D, Path3DCollection  # noqa: F401

from .joints import BONES, HandFrame, JOINT_COUNT
from .kinematics import forward_kinematics


_HAND_COLORS = {"left": "tab:blue", "right": "tab:red"}


class HandViewer:
    def __init__(self, title: str = "XR Hand", view_radius: float = 0.32):
        self.fig = plt.figure(figsize=(8, 6))
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_title(title)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_zlabel("Z")
        r = view_radius
        self.ax.set_xlim(-r, r)
        self.ax.set_ylim(-r, r)
        self.ax.set_zlim(-r, r)
        try:
            self.ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass

        self._scatters: Dict[str, Path3DCollection] = {}
        self._bones: Dict[str, list] = {}
        self._anim: Optional[FuncAnimation] = None

    def _ensure_hand(self, hand: str) -> None:
        if hand in self._scatters:
            return
        color = _HAND_COLORS.get(hand, "k")
        self._scatters[hand] = self.ax.scatter(
            [0] * JOINT_COUNT, [0] * JOINT_COUNT, [0] * JOINT_COUNT,
            c=color, s=22, label=hand,
        )
        lines = []
        for _ in BONES:
            (ln,) = self.ax.plot([0, 0], [0, 0], [0, 0], color=color, lw=1.6)
            lines.append(ln)
        self._bones[hand] = lines
        self.ax.legend(loc="upper right")

    def update_hand(self, frame: HandFrame) -> None:
        hand = frame.hand_side
        self._ensure_hand(hand)
        positions = forward_kinematics(frame)
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        zs = [p[2] for p in positions]
        self._scatters[hand]._offsets3d = (xs, ys, zs)
        for ln, (a, b) in zip(self._bones[hand], BONES):
            ln.set_data_3d([xs[a], xs[b]], [ys[a], ys[b]], [zs[a], zs[b]])

    def run(self, on_tick: Callable[[], None], interval_ms: int = 33) -> None:
        def _update(_):
            on_tick()
            return ()
        self._anim = FuncAnimation(
            self.fig, _update, interval=interval_ms, blit=False,
            cache_frame_data=False,
        )
        plt.show()
