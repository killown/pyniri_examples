#!/usr/bin/env python3
import sys
import time
import os
import struct
import threading
from pywayland.client import Display
from pyniri import NiriSocket

sys.path.insert(0, "/home/neo")

try:
    from niri_protocols.wayland.wl_seat import WlSeat
    from niri_protocols.ext_idle_notify_v1.ext_idle_notifier_v1 import ExtIdleNotifierV1
except ImportError as e:
    print(f"[ERROR] Protocol import failed: {e}")
    sys.exit(1)

IDLE_TIMEOUT_MS = 60000
JOYSTICK_DEV = "/dev/input/js0"
JOYSTICK_DEADZONE = 2000


class NiriIdleDaemon:
    def __init__(self, timeout_ms: int):
        self.timeout_ms = timeout_ms
        self.niri = NiriSocket()
        self.display = Display()
        self.display.connect()

        self.registry = self.display.get_registry()
        self.notifier = None
        self.seat = None
        self.notification_obj = None
        self.is_powered_off = False

        self.registry.dispatcher["global"] = self._global_handler
        self.display.dispatch()
        self.display.roundtrip()

        if not self.notifier or not self.seat:
            print("[ERROR] Required protocols not supported by Niri.", file=sys.stderr)
            sys.exit(1)

        self._setup_idle_notification()

        # Start background joystick monitor
        self.joy_thread = threading.Thread(target=self._joystick_loop, daemon=True)
        self.joy_thread.start()

    def _global_handler(self, registry, id, interface, version):
        if interface == "ext_idle_notifier_v1":
            self.notifier = registry.bind(id, ExtIdleNotifierV1, version)
        elif interface == "wl_seat":
            self.seat = registry.bind(id, WlSeat, version)

    def _setup_idle_notification(self):
        if self.notification_obj:
            self.notification_obj.destroy()

        self.notification_obj = self.notifier.get_input_idle_notification(
            self.timeout_ms, self.seat
        )
        self.notification_obj.dispatcher["idled"] = self._on_idled
        self.notification_obj.dispatcher["resumed"] = self._on_resumed

    def _joystick_loop(self):
        """Monitors joystick and forces a Niri wake-up to reset the timer."""
        fd = None
        while True:
            try:
                if not fd or not os.path.exists(JOYSTICK_DEV):
                    if os.path.exists(JOYSTICK_DEV):
                        fd = os.open(JOYSTICK_DEV, os.O_RDONLY | os.O_NONBLOCK)
                    else:
                        time.sleep(5)
                        continue

                while True:
                    buf = os.read(fd, 8)
                    if not buf:
                        break
                    _, val, ev_type, _ = struct.unpack("IhBB", buf)

                    if not (ev_type & 0x80):
                        if (ev_type == 0x01) or (
                            ev_type == 0x02 and abs(val) > JOYSTICK_DEADZONE
                        ):
                            # JOYSTICK FIX:
                            # Since Niri ignores joystick axes for the idle protocol,
                            # we manually trigger a 'power-on' via IPC. This forces
                            # Niri to reset its internal idle timer and wakes the screen.
                            self.niri.power_on_monitors()
                            self.is_powered_off = False
                            time.sleep(1)  # Throttle
            except (BlockingIOError, OSError):
                time.sleep(0.1)
            except Exception:
                fd = None
                time.sleep(1)

    def _on_idled(self, obj):
        print(f"[{time.strftime('%H:%M:%S')}] IDLE: Powering monitors OFF.", flush=True)
        if self.niri.power_off_monitors():
            self.is_powered_off = True

    def _on_resumed(self, obj):
        if self.is_powered_off:
            print(f"[{time.strftime('%H:%M:%S')}] RESUME: Waking monitors.", flush=True)
            self.niri.power_on_monitors()
            self.is_powered_off = False

    def run(self):
        print(
            f"[INFO] Niri Idle Daemon active (Timeout: {self.timeout_ms / 1000}s)",
            flush=True,
        )
        try:
            while self.display.dispatch(block=True) != -1:
                pass
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down.")
        finally:
            if self.notification_obj:
                self.notification_obj.destroy()
            self.display.disconnect()


if __name__ == "__main__":
    manager = NiriIdleDaemon(IDLE_TIMEOUT_MS)
    manager.run()
