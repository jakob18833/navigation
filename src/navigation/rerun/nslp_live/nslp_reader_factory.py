import serial

from nslpy.v1.nslp_v1_reader import NslpV1Reader

PORT = "/dev/ttyUSB0"
BAUDRATE = 115200


def create() -> NslpV1Reader:
    reader = NslpV1Reader()
    reader.set_byte_stream(serial.serial_for_url(PORT, baudrate=BAUDRATE, timeout=1.0, do_not_open=True))
    return reader
