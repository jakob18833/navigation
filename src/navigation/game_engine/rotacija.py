import sys
from pathlib import Path

# NSLP_DIR = (
#     Path(__file__).resolve().parents[3]
#     / "nslpy"
#     / "nslpy-master"
# )
# 
# sys.path.insert(0, str(NSLP_DIR))

# from src.navigation.nslpy.nslp_reader import *
from navigation.nslpy.nslp_reader import *

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