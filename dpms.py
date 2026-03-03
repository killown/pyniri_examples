#!/usr/bin/env python3
import time
import os
import sys
import struct
from typing import Dict, Optional
from pyniri import NiriSocket

# --- Configuration ---
IDLE_THRESHOLD_SECONDS = 600
POLL_INTERVAL_SECONDS = 1
JOYSTICK_DEV = "/dev/input/js0"
JOYSTICK_DEADZONE = 2000


class JoystickMonitor:
    def __init__(self, device_path: str):
        self.device_path = device_path
        self.fd: Optional[int] = None
        self.active = False
        self._try_open()

    def _try_open(self):
        try:
            if os.path.exists(self.device_path):
                self.fd = os.open(self.device_path, os.O_RDONLY | os.O_NONBLOCK)
                self.active = True
                print(f"[DEBUG] Joystick connected: {self.device_path}", flush=True)
        except Exception:
            self.active = False

    def check_activity(self) -> bool:
        """Returns True if meaningful button/axis movement occurred."""
        if not self.active:
            self._try_open()
            return False

        activity = False
        try:
            while True:
                buf = os.read(self.fd, 8)
                if not buf:
                    break

                # Unpack: time (I), value (h), type (B), number (B)
                _, val, event_type, _ = struct.unpack("IhBB", buf)

                # Mask out the 0x80 'initial state' bit.
                # If the bit was present, it's just a sync event, not fresh activity.
                if not (event_type & 0x80):
                    actual_type = event_type & ~0x80

                    if actual_type == 0x01:  # Button press
                        activity = True
                    elif actual_type == 0x02:  # Axis move
                        if abs(val) > JOYSTICK_DEADZONE:
                            activity = True
        except (BlockingIOError, OSError):
            pass
        except Exception as e:
            print(f"[ERROR] Joystick error: {e}", flush=True)
            self.active = False
            if self.fd:
                os.close(self.fd)

        return activity


def is_focused_window_fullscreen(niri: NiriSocket) -> bool:
    win = niri.get_focused_window()
    if not win:
        return False

    if win.get("is_fullscreen"):
        return True

    layout = win.get("layout", {})
    win_size = layout.get("window_size")
    tile_size = layout.get("tile_size")

    if win_size and tile_size:
        if win_size[0] == int(tile_size[0]) and win_size[1] == int(tile_size[1]):
            if win_size[0] > 1000:
                return True
    return False


def main():
    print(
        f"[DEBUG] Niri DPMS started. Threshold: {IDLE_THRESHOLD_SECONDS}s", flush=True
    )

    niri = NiriSocket()
    joy = JoystickMonitor(JOYSTICK_DEV)

    last_cursor_pos: Optional[Dict[str, float]] = None
    idle_counter = 0
    is_powered_off = False

    while True:
        try:
            current_cursor = niri.get_cursor_position()
            joy_activity = joy.check_activity()

            # Check if mouse actually moved
            mouse_moved = (
                last_cursor_pos is not None and current_cursor != last_cursor_pos
            )

            if mouse_moved or joy_activity:
                if is_powered_off:
                    source = "Mouse" if mouse_moved else "Joystick"
                    print(
                        f"[DEBUG] {source} activity detected. Powering monitors ON.",
                        flush=True,
                    )
                    # Explicitly wake monitors
                    niri.power_on_monitors()
                    is_powered_off = False

                idle_counter = 0
            else:
                if is_focused_window_fullscreen(niri):
                    if idle_counter > 0:
                        print(
                            "[DEBUG] Inhibited by fullscreen focused window.",
                            flush=True,
                        )
                    idle_counter = 0
                else:
                    idle_counter += POLL_INTERVAL_SECONDS

            # Power off logic
            if idle_counter >= IDLE_THRESHOLD_SECONDS and not is_powered_off:
                print(
                    f"[DEBUG] {idle_counter}s idle. Powering monitors OFF.", flush=True
                )
                if niri.power_off_monitors():
                    is_powered_off = True
                    idle_counter = 0

            last_cursor_pos = current_cursor

        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr, flush=True)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
