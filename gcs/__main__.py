"""Entry point: ``python -m gcs`` launches the cockpit.

Examples:
    python -m gcs                                  # offline (synthetic feed)
    python -m gcs --connect udpout:127.0.0.1:14550 # ArduPilot SITL / sim_vehicle
    python -m gcs --connect /dev/ttyACM0           # real Pixhawk over USB
    python -m gcs --connect udpout:10.0.0.5:14550 --video rtsp://10.0.0.5:8554/eo
"""

from .app import run


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="TaloNet GCS manual teleop cockpit")
    ap.add_argument("--connect", default=None,
                    help="MAVLink endpoint (udpout:host:port, serial path, ...)")
    ap.add_argument("--video", default=None,
                    help="EO/IR video source (device index or RTSP/UDP URL)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    a = ap.parse_args()
    run(connect=a.connect, video=a.video, window=(a.width, a.height))


if __name__ == "__main__":
    main()
