import logging
import sys
from pathlib import Path

# Add current directory to path for imports (before stdlib)
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# Import io module from testbench directory specifically
import importlib.util
io_spec = importlib.util.spec_from_file_location("modbus_io", Path(__file__).parent / "io.py")
modbus_io = importlib.util.module_from_spec(io_spec)
io_spec.loader.exec_module(modbus_io)

TestbenchController = modbus_io.IOController

# Built-in TOML parser support
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_labels_or_addresses(arg: str) -> list:
    """Parse comma-separated labels or bit numbers."""
    items = [item.strip() for item in arg.split(",")]
    result = []
    for item in items:
        if item.isdigit():
            result.append(int(item))
        else:
            result.append(item)
    return result


def interactive_mode(tb: TestbenchController, labels: list[str]):
    """Interactive mode - toggle outputs by pressing Enter."""
    # Validate all labels exist first
    valid_labels = []
    for label in labels:
        if tb._get_output_address(label) is not None:
            valid_labels.append(label)
        else:
            logger.warning(f"Invalid label: {label}")

    if not valid_labels:
        logger.error("No valid labels provided.")
        return

    # Show current status
    print("\n=== Interactive Output Control ===")
    print("Press Enter to toggle each output. Press Ctrl+C to exit.\n")

    # Initial state display
    states = tb.read_inputs()
    if states:
        for label in valid_labels:
            is_on = states.get(label, False)
            print(f" {label.ljust(20)} : {'[ ON ]' if is_on else '[ OFF ]'}")

    print()

    try:
        while True:
            for label in valid_labels:
                current_state = tb.read_inputs()
                is_on = current_state.get(label, False) if current_state else None

                # Show prompt and wait for Enter
                status = "[ ON ]" if (is_on is not None and is_on) else "[ OFF ]"
                user_input = input(f"Toggle {label} ({status}): ")

                if user_input == "":
                    # Toggle the output
                    new_state = not (is_on if is_on is not None else False)
                    tb.write_output_by_label(label, new_state)

                    # Refresh and show updated state
                    current_state = tb.read_inputs()
                    is_on = current_state.get(label, False) if current_state else None
                    status = "[ ON ]" if (is_on is not None and is_on) else "[ OFF ]"
                    print(f"  -> {label}: {status}\n")
                elif user_input.lower() in ["q", "quit", "exit"]:
                    print("Exiting...")
                    return
                else:
                    # Show current state for non-Enter input
                    print(f"  -> {label}: {status}\n")

    except KeyboardInterrupt:
        logger.info("\nInteractive mode interrupted by user.")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Testbench IO Control Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Toggle outputs by label
  python cli.py --label PLC_XL_IN0

  # Toggle multiple labels
  python cli.py --label "PLC_XL_IN0,PLC_XL_IN1"

  # Toggle outputs by coil address
  python cli.py --bit 6,7

  # Set specific state (0=OFF, 1=ON)
  python cli.py --label "USB_PLC_M,USB_PLC_XL" --state 1

  # Interactive mode
  python cli.py --label "USB_PLC_M,USB_PLC_XL" --interactive
        """
    )

    parser.add_argument("--label", "-l", type=str,
                        help="Output label(s) to control (comma-separated)")
    parser.add_argument("--bit", "-b", type=str,
                        help="Coil bit address(es) to control (comma-separated)")
    parser.add_argument("--state", "-s", type=int, choices=[0, 1], default=1,
                        help="Output state: 0=OFF, 1=ON (default: 1)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive mode - press Enter to toggle")
    parser.add_argument("--read", "-r", action="store_true",
                        help="Read and display current input status")
    parser.add_argument("--list", "-L", action="store_true",
                        help="List all available output labels and their addresses")

    args = parser.parse_args()

    tb = TestbenchController()

    if not tb.connect():
        sys.exit(1)

    try:
        if args.list:
            print("\n=== Available Outputs ===")
            for addr_str, label in tb.output_map["labels"].items():
                print(f"  {label.ljust(20)} -> Coil {addr_str}")
            print()
            sys.exit(0)

        if args.read:
            print("\n=== Current Input Status ===")
            states = tb.read_inputs()
            if states:
                for label, is_active in states.items():
                    print(f" {label.ljust(20)} : {'[ POWER / SIGNAL ]' if is_active else '[ OFF ]'}")
            print()
            sys.exit(0)

        if args.interactive:
            if not args.label:
                parser.error("--label is required for interactive mode")
            labels = parse_labels_or_addresses(args.label)
            if not all(isinstance(l, str) for l in labels):
                parser.error("Interactive mode requires label names, not bit numbers")
            interactive_mode(tb, labels)

        elif args.label:
            labels = parse_labels_or_addresses(args.label)
            state = bool(args.state)

            # Collect all addresses for write
            label_map = {}  # address -> label
            for label in labels:
                if isinstance(label, str):
                    addr = tb._get_output_address(label)
                    if addr is not None:
                        label_map[addr] = label
                    else:
                        print(f"  {label}: NOT_FOUND")

            if label_map:
                addresses = sorted(label_map.keys())
                success = tb.write_coils(addresses, state)

                print("\n=== Write Results ===")
                for addr in addresses:
                    label = label_map[addr]
                    status = "SUCCESS" if success else "FAILED"
                    print(f"  {label}: {status}")

        elif args.bit:
            bit_numbers = parse_labels_or_addresses(args.bit)
            if not all(isinstance(b, int) for b in bit_numbers):
                parser.error("--bit requires numeric addresses")
            state = bool(args.state)

            # Validate all addresses exist first
            valid_addresses = []
            for addr in bit_numbers:
                label = tb._get_label_by_address(addr)
                if label is None:
                    print(f"  {addr}: NOT_FOUND")
                else:
                    valid_addresses.append(addr)

            if valid_addresses:
                addresses = sorted(valid_addresses)
                success = tb.write_coils(addresses, state)

                print("\n=== Write Results ===")
                for addr in addresses:
                    label = tb._get_label_by_address(addr)
                    status = "SUCCESS" if success else "FAILED"
                    print(f"  {label} ({addr}): {status}")

        else:
            parser.print_help()

    finally:
        tb.close()


if __name__ == "__main__":
    main()