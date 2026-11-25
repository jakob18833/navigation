""" ? NSLP telemetry from the NAV_BOX -> Rerun viewer, live from the serial port or replayed from a raw capture.

main.py            command line, wires the pieces below together
byte_sources.py    where the bytes come from (serial port + capture tee, or a capture file)
packet_logging.py  what each decoded packet becomes in Rerun (plots, map, 3D attitude)
viewer_layout.py   how the Rerun viewer window is arranged
"""
