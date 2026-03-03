#!/usr/bin/env python3
import time
import sys
from typing import Dict, Optional
from pyniri import NiriSocket

# --- Configuration ---
IDLE_THRESHOLD_SECONDS = 10
POLL_INTERVAL_SECONDS = 1


def is_focused_window_fullscreen(niri: NiriSocket) -> bool:
    """
    Checks if the currently focused window is fullscreen.
    """
    win = niri.get_focused_window()
    if not win:
        return False

    # Check for explicit fullscreen flag
    if win.get("is_fullscreen"):
        return True

    # Fallback: Check if window dimensions match tile dimensions exactly
    layout = win.get("layout", {})
    win_size = layout.get("window_size")
    tile_size = layout.get("tile_size")

    if win_size and tile_size:
        # If sizes match exactly, it is effectively filling its container/screen
        if win_size[0] == int(tile_size[0]) and win_size[1] == int(tile_size[1]):
            # Ensure it's not a tiny window (like a floating terminal)
            if win_size[0] > 1000:
                return True

    return False


def main():
    print(
        f"[DEBUG] Niri Focused-DPMS started. Threshold: {IDLE_THRESHOLD_SECONDS}s",
        flush=True,
    )

    niri = NiriSocket()
    last_cursor_pos: Optional[Dict[str, float]] = None
    idle_counter = 0
    is_powered_off = False

    while True:
        try:
            current_cursor = niri.get_cursor_position()

            # Activity Detection
            if last_cursor_pos is not None and current_cursor != last_cursor_pos:
                if is_powered_off:
                    print("[DEBUG] Activity: Mouse move. Resetting idle.", flush=True)
                    is_powered_off = False
                idle_counter = 0
            else:
                # Check if focused window inhibits DPMS
                if is_focused_window_fullscreen(niri):
                    if idle_counter > 0:
                        print(
                            "[DEBUG] Inhibited: Focused window is fullscreen.",
                            flush=True,
                        )
                    idle_counter = 0
                else:
                    idle_counter += POLL_INTERVAL_SECONDS

            # Trigger DPMS Off
            if idle_counter >= IDLE_THRESHOLD_SECONDS and not is_powered_off:
                print(
                    f"[DEBUG] {idle_counter}s reached. Powering off monitors.",
                    flush=True,
                )
                # Corrected: power_off_monitors in pyniri should send {"Action": "PowerOffMonitors"}
                if niri.power_off_monitors():
                    is_powered_off = True

            last_cursor_pos = current_cursor

        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr, flush=True)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
