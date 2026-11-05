# NSLP Reader - Noordung Serial Link Protocol

Python reader for STM32 NSLP protocol implementation.

## Features

- Reads NSLP packets from STM32 devices via USB/UART
- Automatically loads all packet type configurations from `json packet configs/` folder
- Supports multiple packet types (GPS, BNO055, BMP180, etc.)
- Hardware CRC-32 verification (STM32 compatible)
- Clean packet display with parsed field values

## Protocol Structure

```
[0x7E][Sender][Receiver][Type][Size][Payload...][CRC32]
```

- **Start Byte**: `0x7E`
- **Sender**: 1 byte (source address)
- **Receiver**: 1 byte (destination address)
- **Type**: 1 byte (packet type ID)
- **Size**: 1 byte (payload length, 0-255)
- **Payload**: Variable length data
- **CRC32**: 4 bytes (little-endian, calculated over Sender+Receiver+Type+Size+Payload)

## Supported Packet Types

The reader automatically loads all configurations from `json packet configs/`:

- **Type 10**: Position_GPS (latitude, longitude, altitude, fixType, numSV, timestamp)
- **Type 11**: BNO055_payload (calibration, gyro, accel, magnetometer data)
- **Type 12**: BMP_payload (temperature, pressure, timestamp)

## Usage

### Basic Usage

```bash
python nslp_reader.py
```

The reader will:
1. Load all config files from `json packet configs/` folder
2. Use the serial port specified in the config files
3. Display all received packets with parsed data

### Specify Serial Port

```bash
python nslp_reader.py COM9        # Windows
python nslp_reader.py /dev/ttyUSB0  # Linux
```

### Example Output

```
NSLP Protocol Reader
============================================================

Loading configurations from 4 file(s):
  ✓ .config_BMP: 1 packet type(s)
  ✓ .config_BNO055: 1 packet type(s)
  ✓ .config_GPS: 1 packet type(s)
  ✓ config.json: 1 packet type(s)

Total packet types loaded: 3
Serial port: COM9

Configured packet types:
  Type 10: Position_GPS (6 fields)
  Type 11: BNO055_payload (11 fields)
  Type 12: BMP_payload (3 fields)

Connected to COM9 at 115200 baud

NSLP Reader started. Listening on COM9...
Press Ctrl+C to stop

============================================================
Packet received at 14:32:15
------------------------------------------------------------
Sender:   0x01
Receiver: 0xFF
Type:     10
Size:     24 bytes
CRC:      0x12345678 ✓
Type Name: Position_GPS
------------------------------------------------------------
Parsed Data:
  latitude       : 46.123456
  longitude      : 14.987654
  altitude       : 512.340000
  fixType        : 3
  numSV          : 12
  timestamp      : 1234567890
============================================================
```

## Configuration Files

Each config file in `json packet configs/` should follow this format:

```json
{
    "address": "COM9",
    "mockTypes": {
        "10": {
            "name": "Position_GPS",
            "fields": [
                {
                    "name": "latitude",
                    "type": "FLOAT"
                },
                {
                    "name": "longitude",
                    "type": "FLOAT"
                }
            ]
        }
    }
}
```

### Supported Field Types

- `FLOAT` / `float` - 4 bytes, IEEE 754 single precision
- `DOUBLE` / `double` - 8 bytes, IEEE 754 double precision
- `INT` / `int` - 4 bytes, signed integer
- `UINT` / `uint` - 4 bytes, unsigned integer
- `SHORT` / `short` - 2 bytes, signed integer
- `USHORT` / `ushort` - 2 bytes, unsigned integer
- `BYTE` / `byte` - 1 byte, unsigned
- `CHAR` / `char` - 1 byte, ASCII character

All multi-byte values use little-endian byte order.

## STM32 Implementation

The corresponding STM32 sender implementation can be found in:
- `NAV_BOX/Core/Inc/nslp_dma.h`
- `NAV_BOX/Core/Src/nslp_dma.c`

Key STM32 features:
- DMA-based transmission and reception
- Hardware CRC-32 peripheral (CRC-32/MPEG-2)
- Packet queuing system
- Interrupt-driven operation

## Requirements

```bash
pip install pyserial crcmod
```

## CRC Calculation

The reader uses CRC-32/MPEG-2 to match STM32 hardware CRC:
- Polynomial: 0x04C11DB7
- Initial value: 0xFFFFFFFF
- MSB first processing
- No input/output bit reversal
- No final XOR

## Troubleshooting

### Port Not Found
- Windows: Check Device Manager for COM port number
- Linux: Check `ls /dev/tty*` and ensure permissions (`sudo chmod 666 /dev/ttyUSB0`)

### CRC Mismatch
- Verify STM32 is using hardware CRC peripheral
- Check that packet structure matches exactly
- Ensure little-endian byte order for CRC

### No Packets Received
- Verify baudrate matches STM32 configuration (default: 115200)
- Check physical connections (TX/RX not crossed)
- Verify STM32 is transmitting (check with oscilloscope/logic analyzer)

## License

This code is part of the Noordung Labs NSLP implementation.
