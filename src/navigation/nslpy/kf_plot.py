#!/usr/bin/env python3
"""Live plotter for NSLP packet type 15 (KF_payload)."""

import struct, sys, collections
import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from crc import CRC32

PORT     = "COM5"
BAUD     = 9600
MAX_PTS  = 100   # rolling window
KF_TYPE  = 15

# ── packet primitives ────────────────────────────────────────────────────────

def calc_crc(data: bytes) -> int:
    return CRC32.update(CRC32.init(), data)

def read_exact(ser, n: int) -> bytes | None:
    buf = ser.read(n)
    return buf if len(buf) == n else None

def read_packet(ser):
    """Return (sender, receiver, type, payload) or None."""
    while True:
        b = ser.read(1)
        if not b:
            return None
        if b[0] == 0x7E:
            break
    hdr = read_exact(ser, 4)
    if hdr is None:
        return None
    sender, receiver, ptype, size = hdr
    payload = read_exact(ser, size) if size else b''
    if payload is None:
        return None
    crc_bytes = read_exact(ser, 4)
    if crc_bytes is None:
        return None
    expected = struct.unpack('<I', crc_bytes)[0]
    if calc_crc(bytes([sender, receiver, ptype, size]) + payload) != expected:
        return None
    return sender, receiver, ptype, payload

# ── KF payload parser ────────────────────────────────────────────────────────

def parse_kf(payload: bytes):
    """Return (Xx, Xy, Xz, timestamp) or None."""
    if len(payload) < 28:   # 3×8 + 1×4
        return None
    xx, xy, xz = struct.unpack_from('<3d', payload, 0)
    ts,          = struct.unpack_from('<i',  payload, 24)
    return xx, xy, xz, ts

# ── live plot ────────────────────────────────────────────────────────────────

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else PORT

    ser = serial.Serial(port, BAUD, timeout=1)
    print(f"Connected to {port} @ {BAUD}. Ctrl-C to quit.")

    ts  = collections.deque(maxlen=MAX_PTS)
    xx  = collections.deque(maxlen=MAX_PTS)
    xy  = collections.deque(maxlen=MAX_PTS)
    xz  = collections.deque(maxlen=MAX_PTS)

    fig, ax = plt.subplots()
    l_xx, = ax.plot([], [], label='Xx')
    l_xy, = ax.plot([], [], label='Xy')
    l_xz, = ax.plot([], [], label='Xz')
    ax.legend(); ax.set_xlabel('timestamp'); ax.set_ylabel('estimation')
    ax.set_title('KF_payload – live')

    def update(_):
        pkt = read_packet(ser)
        if pkt and pkt[2] == KF_TYPE:
            parsed = parse_kf(pkt[3])
            if parsed:
                vxx, vxy, vxz, vts = parsed
                ts.append(vts); xx.append(vxx); xy.append(vxy); xz.append(vxz)
                for line, data in ((l_xx, xx), (l_xy, xy), (l_xz, xz)):
                    line.set_data(ts, data)
                ax.relim(); ax.autoscale_view()
        return l_xx, l_xy, l_xz

    ani = animation.FuncAnimation(fig, update, interval=50, blit=True, cache_frame_data=False)
    try:
        plt.show()
    finally:
        ser.close()

if __name__ == '__main__':
    main()
