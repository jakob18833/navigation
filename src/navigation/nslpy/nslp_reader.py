#!/usr/bin/env python3
"""
NSLP (Noordung Serial Link Protocol) Reader
Reads data from STM32F303K8 board via USB/UART
Protocol structure:
    [0x7E][Sender][Receiver][Type][Size][Payload...][CRC32]
"""

import serial
import struct
import json
import sys
import time
import os
import argparse
from collections import deque
from typing import Dict, Any, Optional, Tuple, List
from crc import CRC32


class NSLPPacket:
    """Represents an NSLP protocol packet"""
    START_BYTE = 0x7E
    HEADER_SIZE = 5  # Start + Sender + Receiver + Type + Size
    CRC_SIZE = 4
    
    def __init__(self):
        self.start_byte = 0x7E
        self.sender = 0
        self.receiver = 0
        self.type = 0
        self.size = 0
        self.payload = b''
        self.crc = 0
    
    def __repr__(self):
        return (f"NSLPPacket(sender=0x{self.sender:02X}, receiver=0x{self.receiver:02X}, "
                f"type={self.type}, size={self.size})")


class NSLPReader:
    """NSLP protocol reader for STM32 communication"""

    FIELD_SIZES = {
        'FLOAT': 4,
        'DOUBLE': 8,
        'INT': 4,
        'UINT': 4,
        'SHORT': 2,
        'USHORT': 2,
        'BYTE': 1,
        'CHAR': 1,
    }
    
    def __init__(self, port: str = None, baudrate: int = 115200):
        """
        Initialize NSLP reader
        
        Args:
            port: Serial port (e.g., 'COM9' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Communication speed (default: 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.packet_types = {}
        self.running = False
        self.config_file = None
        self.filter_type = None
        self.plot_window = None
        self.plot_fields = []
        self.plot_series = {}
        self.plot_samples = deque()
        self.plot_sample_index = 0
        self.plot_enabled = False
        self._plot_figure = None
        self._plot_axes = None
        self._plot_lines = {}

    def _parse_packet_type(self, packet_type: Optional[Any]) -> Optional[int]:
        if packet_type is None:
            return None
        if isinstance(packet_type, str):
            return int(packet_type, 0)
        return int(packet_type)

    def set_filter_type(self, packet_type: Optional[Any]) -> None:
        """Set the packet type accepted by the reader."""
        self.filter_type = self._parse_packet_type(packet_type)

    def _extract_port_from_config(self, config: Dict[str, Any]) -> Optional[str]:
        """Return the serial port configured in a JSON file, if present."""
        port = config.get('address')
        if port:
            return port

        port_override = config.get('addressOverride')
        if port_override:
            return port_override

        return None

    def _resolve_config_path(self, config_file: str) -> str:
        """Resolve a config file or a config folder to a concrete JSON file."""
        if os.path.isdir(config_file):
            return os.path.join(config_file, 'config.json')
        return config_file

    def should_accept_packet(self, packet: NSLPPacket) -> bool:
        """Return True when a packet matches the active filter."""
        return self.filter_type is None or packet.type == self.filter_type

    def _select_plot_fields(self, type_def: Dict[str, Any]) -> List[str]:
        fields = []
        for field in type_def.get('fields', []):
            field_type = field.get('type', '').upper()
            if field_type in self.FIELD_SIZES and field_type != 'CHAR':
                fields.append(field['name'])
        return fields

    def _setup_plot(self, type_def: Dict[str, Any], window_size: int) -> None:
        self.plot_window = window_size
        self.plot_fields = self._select_plot_fields(type_def)
        self.plot_series = {field: deque(maxlen=window_size) for field in self.plot_fields}
        self.plot_samples = deque(maxlen=window_size)
        self.plot_sample_index = 0
        self.plot_enabled = bool(self.plot_fields)

        if not self.plot_enabled:
            print("Plotting disabled: selected packet type has no numeric fields.")
            return

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("Plotting disabled: matplotlib is not installed.")
            self.plot_enabled = False
            return

        self._plt = plt
        self._plot_figure, self._plot_axes = plt.subplots(len(self.plot_fields), 1, sharex=True, figsize=(10, 2.5 * len(self.plot_fields)))
        if len(self.plot_fields) == 1:
            self._plot_axes = [self._plot_axes]

        for axis, field in zip(self._plot_axes, self.plot_fields):
            line, = axis.plot([], [], lw=1.5)
            axis.set_title(field)
            axis.grid(True, alpha=0.3)
            self._plot_lines[field] = line

        self._plot_figure.tight_layout()

    def _update_plot(self, packet: NSLPPacket, parsed: Dict[str, Any]) -> None:
        if not self.plot_enabled or self._plot_figure is None:
            return

        sample_index = self.plot_sample_index
        self.plot_sample_index += 1
        self.plot_samples.append(sample_index)

        for field in self.plot_fields:
            value = parsed.get(field)
            if isinstance(value, (int, float)):
                self.plot_series[field].append(value)
            else:
                self.plot_series[field].append(float('nan'))

        x_values = list(self.plot_samples)
        for axis, field in zip(self._plot_axes, self.plot_fields):
            y_values = list(self.plot_series[field])
            self._plot_lines[field].set_data(x_values, y_values)
            axis.relim()
            axis.autoscale_view()
            if x_values:
                axis.set_xlim(x_values[0], max(x_values[0] + 1, x_values[-1] + 1))

        self._plot_figure.canvas.draw_idle()
        self._plot_figure.canvas.flush_events()

    def _field_size(self, field_type: str) -> int:
        return self.FIELD_SIZES.get(field_type.upper(), 0)

    def _expected_payload_size(self, type_def: Dict[str, Any]) -> Optional[int]:
        total = 0
        for field in type_def.get('fields', []):
            size = self._field_size(field.get('type', ''))
            if not size:
                return None
            total += size
        return total

    def _format_payload_hex(self, payload: bytes) -> None:
        if not payload:
            print("  (empty)")
            return

        hex_str = payload.hex()
        for i in range(0, len(hex_str), 32):
            print(f"  {hex_str[i:i + 32]}")

    def _unpack_field(self, payload: bytes, offset: int, field_type: str) -> Tuple[Optional[Any], int]:
        field_type = field_type.upper()
        if field_type == 'FLOAT':
            return struct.unpack_from('<f', payload, offset)[0], offset + 4
        if field_type == 'DOUBLE':
            return struct.unpack_from('<d', payload, offset)[0], offset + 8
        if field_type == 'INT':
            return struct.unpack_from('<i', payload, offset)[0], offset + 4
        if field_type == 'UINT':
            return struct.unpack_from('<I', payload, offset)[0], offset + 4
        if field_type == 'SHORT':
            return struct.unpack_from('<h', payload, offset)[0], offset + 2
        if field_type == 'USHORT':
            return struct.unpack_from('<H', payload, offset)[0], offset + 2
        if field_type == 'BYTE':
            return payload[offset], offset + 1
        if field_type == 'CHAR':
            return chr(payload[offset]), offset + 1
        return f"<unsupported type: {field_type}>", offset

    def load_config(self, config_file: str = None) -> bool:
        """Load packet type definitions from config.json."""
        config_path = self._resolve_config_path(config_file or os.path.join(
            os.path.dirname(__file__), 'json packet configs', 'config.json'))

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file '{config_path}' not found.")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing config file '{config_path}': {e}")
            return False

        self.config_file = config_path
        self.packet_types = config.get('mockTypes', {})

        port = self._extract_port_from_config(config)
        if port:
            self.port = port

        print(f"Loaded config: {os.path.basename(config_path)}")
        print(f"Loaded packet types: {len(self.packet_types)}")
        if self.port:
            print(f"Serial port: {self.port}")

        if self.packet_types:
            print("\nConfigured packet types:")
            for type_id, type_def in sorted(self.packet_types.items(), key=lambda x: int(x[0])):
                type_name = type_def.get('name', 'Unknown')
                field_count = len(type_def.get('fields', []))
                expected_size = self._expected_payload_size(type_def)
                size_text = f", {expected_size} bytes" if expected_size is not None else ""
                print(f"  Type {type_id}: {type_name} ({field_count} fields{size_text})")

        return True
    
    def connect(self) -> bool:
        """Establish serial connection"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected")
    
    def calculate_crc32(self, data: bytes) -> int:
        """
        Calculate CRC32 using the CRC32 class from crc.py
        
        Args:
            data: bytes to calculate CRC for
            
        Returns:
            32-bit CRC value
        """
        crc = CRC32.init()
        crc = CRC32.update(crc, data)
        return crc
    
    def read_packet(self) -> Optional[NSLPPacket]:
        """
        Read and parse one NSLP packet from serial port
        
        Returns:
            NSLPPacket object if successful, None otherwise
        """
        if not self.serial or not self.serial.is_open:
            return None
        
        try:
            # Search for start byte
            while True:
                byte = self.serial.read(1)
                if not byte:
                    return None
                if byte[0] == NSLPPacket.START_BYTE:
                    break
            
            # Read header (Sender, Receiver, Type, Size)
            header = self.serial.read(4)
            if len(header) < 4:
                print("Error: Incomplete header")
                return None
            
            packet = NSLPPacket()
            packet.sender = header[0]
            packet.receiver = header[1]
            packet.type = header[2]
            packet.size = header[3]
            
            # Read payload
            if packet.size > 0:
                packet.payload = self.serial.read(packet.size)
                if len(packet.payload) < packet.size:
                    print(f"Error: Incomplete payload (expected {packet.size}, got {len(packet.payload)})")
                    return None
            
            # Read CRC (4 bytes, little-endian)
            crc_bytes = self.serial.read(4)
            if len(crc_bytes) < 4:
                print("Error: Incomplete CRC")
                return None
            
            packet.crc = struct.unpack('<I', crc_bytes)[0]
            
            # Verify CRC
            # CRC is calculated over: Sender + Receiver + Type + Size + Payload
            # (NOT including the start byte 0x7E)
            crc_data = bytes([packet.sender, packet.receiver, 
                             packet.type, packet.size]) + packet.payload
            calculated_crc = self.calculate_crc32(crc_data)
            
            if calculated_crc != packet.crc:
                print(f"Warning: CRC mismatch! Expected 0x{packet.crc:08X}, got 0x{calculated_crc:08X}")
                return None
            
            return packet
            
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    
    def parse_payload(self, packet: NSLPPacket) -> Dict[str, Any]:
        """
        Parse packet payload based on type definition
        
        Args:
            packet: NSLPPacket with payload to parse
            
        Returns:
            Dictionary with parsed fields
        """
        packet_type_str = str(packet.type)
        if packet_type_str not in self.packet_types:
            return {'raw_data': packet.payload.hex(), 'error': 'Unknown packet type'}
        
        type_def = self.packet_types[packet_type_str]
        fields = type_def.get('fields', [])
        parsed = {}
        offset = 0
        expected_size = self._expected_payload_size(type_def)
        if expected_size is not None and expected_size != packet.size:
            parsed['_warning'] = f"config expects {expected_size} bytes, packet has {packet.size}"
        
        for field in fields:
            field_name = field['name']
            field_type = field['type']
            
            try:
                field_size = self._field_size(field_type)
                if not field_size:
                    parsed[field_name] = f"<unsupported type: {field_type}>"
                elif offset + field_size <= len(packet.payload):
                    value, offset = self._unpack_field(packet.payload, offset, field_type)
                    parsed[field_name] = value
                else:
                    parsed[field_name] = None
                        
            except struct.error as e:
                print(f"Error parsing field '{field_name}': {e}")
                parsed[field_name] = None
        
        return parsed
    
    def display_packet(self, packet: NSLPPacket):
        """Display packet information in a readable format"""
        if not self.should_accept_packet(packet):
            return

        print("\n" + "="*60)
        print(f"Packet received at {time.strftime('%H:%M:%S')}")
        print("-"*60)
        print(f"Sender:   0x{packet.sender:02X}")
        print(f"Receiver: 0x{packet.receiver:02X}")
        print(f"Type:     {packet.type}")
        print(f"Size:     {packet.size} bytes")
        print(f"CRC:      0x{packet.crc:08X} ✓")
        
        # Get packet type name if defined
        packet_type_str = str(packet.type)
        if packet_type_str in self.packet_types:
            type_name = self.packet_types[packet_type_str].get('name', 'Unknown')
            print(f"Type Name: {type_name}")
            expected_size = self._expected_payload_size(self.packet_types[packet_type_str])
            if expected_size is not None and expected_size != packet.size:
                print(f"Warning: config expects {expected_size} payload bytes")
            print("-"*60)
            
            # Parse and display fields
            parsed = self.parse_payload(packet)
            
            if 'error' in parsed:
                print(f"Error: {parsed['error']}")
                print("Raw Payload (hex):")
                self._format_payload_hex(packet.payload)
            else:
                print("Parsed Data:")
                for key, value in parsed.items():
                    if key == '_warning':
                        print(f"  warning        : {value}")
                        continue
                    if key != 'raw_data':
                        if value is not None:
                            if isinstance(value, float):
                                print(f"  {key:15s}: {value:.6f}")
                            else:
                                print(f"  {key:15s}: {value}")
                        else:
                            print(f"  {key:15s}: <missing>")

                self._update_plot(packet, parsed)
        else:
            print(f"Type Name: Unknown (Type {packet.type} not in configs)")
            print("-"*60)
            print("Raw Payload (hex):")
            self._format_payload_hex(packet.payload)
        
        print("="*60)
    
    def run(self):
        """Main loop - continuously read and display packets"""
        print(f"\nNSLP Reader started. Listening on {self.port}...")
        if self.filter_type is not None:
            print(f"Filtering to packet type 0x{self.filter_type:02X}")
        if self.plot_enabled:
            print(f"Plotting last {self.plot_window} samples")
        print("Press Ctrl+C to stop\n")

        if self.plot_enabled:
            self._plt.ion()
            self._plot_figure.show()
        
        self.running = True
        packet_count = 0
        
        try:
            while self.running:
                packet = self.read_packet()
                if packet and self.should_accept_packet(packet):
                    packet_count += 1
                    print(f"\n[Packet #{packet_count}]")
                    self.display_packet(packet)

                    if self.plot_enabled:
                        self._plt.pause(0.001)
                    
        except KeyboardInterrupt:
            print("\n\nStopping reader...")
        finally:
            self.running = False
            if self.plot_enabled:
                self._plt.ioff()
            print(f"\nTotal packets received: {packet_count}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NSLP Protocol Reader')
    parser.add_argument('port', nargs='?', help='Serial port override, e.g. COM9')
    parser.add_argument('--filter', dest='filter_type', help='Only accept packets with this type id (decimal or hex, e.g. 10 or 0x0A)')
    parser.add_argument('--plot', dest='plot_window', type=int, help='Plot the filtered packet data with this rolling window size')
    parser.add_argument('--config', default=os.path.join(os.path.dirname(__file__), 'json packet configs', 'config.json'), help='Path to config.json')
    parser.add_argument('--baudrate', type=int, default=9600, help='Serial baud rate')
    args = parser.parse_args()

    print("NSLP Protocol Reader")
    print("="*60)

    reader = NSLPReader(port=args.port, baudrate=args.baudrate)
    if args.port:
        print(f"Using port from command line: {args.port}")

    if args.filter_type is not None:
        try:
            reader.set_filter_type(args.filter_type)
        except ValueError as exc:
            print(f"Error: invalid packet type for --filter: {args.filter_type} ({exc})")
            return 1
        print(f"Filtering packets to type: 0x{reader.filter_type:02X}")

    if not reader.load_config(args.config):
        return 1

    if args.plot_window is not None:
        if args.plot_window <= 0:
            print("Error: --plot window size must be greater than 0")
            return 1
        if reader.filter_type is None:
            print("Error: --plot requires --filter to select a packet type")
            return 1

        type_key = str(reader.filter_type)
        type_def = reader.packet_types.get(type_key)
        if not type_def:
            print(f"Error: filtered packet type 0x{reader.filter_type:02X} is not defined in config.json")
            return 1

        reader._setup_plot(type_def, args.plot_window)
        if not reader.plot_enabled:
            return 1
    
    # Check if we have a port configured
    if not reader.port:
        print("\nError: No serial port specified.")
        print("Either:")
        print("  1. Add 'address' or 'addressOverride' to config.json")
        print("  2. Pass port as command line argument: python nslp_reader.py COM9 --filter 10 --plot 50")
        return 1
    
    # Connect to serial port
    if not reader.connect():
        print("\nFailed to connect. Please check:")
        print("  1. Port name is correct")
        print("  2. Device is connected")
        print("  3. No other program is using the port")
        print(f"  4. Device permissions (on Linux, try: sudo chmod 666 {reader.port})")
        return 1
    
    try:
        # Run the reader
        reader.run()
    finally:
        # Clean up
        reader.disconnect()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
