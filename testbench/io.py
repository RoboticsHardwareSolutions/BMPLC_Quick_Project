import logging
import sys
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

# Built-in TOML parser support
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class IOController:
    def __init__(self, config_path="testbench.toml"):
        # Load configuration from file
        with open(config_path, "rb") as f:
            self.config = tomllib.load(f)["io"]

        self.conn = self.config["connection"]
        self.output_map = self.config["map"]["outputs"]

        # Initialize Modbus RTU client
        self.client = ModbusSerialClient(
            port=self.conn["port"],
            baudrate=self.conn["baudrate"],
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self.conn["timeout"]
        )

    def connect(self) -> bool:
        if not self.client.connect():
            logger.error(f"Failed to open serial port: {self.conn['port']}")
            return False
        logger.info(f"Port {self.conn['port']} successfully opened.")
        return True

    def close(self):
        self.client.close()
        logger.info("Connection to port closed.")

    def read_inputs(self) -> dict | None:
        """Reads Holding registers and parses them into named bits."""
        reg_map = self.config["map"]["inputs"]
        slave_id = self.conn["inputs_id"]  # ID for inputs block from [io.connection]

        if reg_map["register_type"] != "holding":
            logger.error("Configuration error: expected 'holding' type for inputs section.")
            return None

        try:
            # Read sequence of 16-bit registers
            response = self.client.read_holding_registers(
                address=reg_map["start_address"],
                count=reg_map["count"],
                device_id=slave_id
            )

            if response.isError():
                logger.error(f"Modbus read error for inputs (Slave {slave_id}): {response}")
                return None

            # Combine list of 16-bit registers into single bit mask
            combined_bits = 0
            for i, reg_value in enumerate(response.registers):
                combined_bits |= (reg_value << (i * 16))

            # Parse mask by named bits
            results = {}
            for bit_str, label in reg_map["labels"].items():
                bit_idx = int(bit_str)
                bit_value = (combined_bits >> bit_idx) & 1
                results[label] = bool(bit_value)

            return results

        except ModbusException as e:
            logger.error(f"Modbus exception while reading inputs: {e}")
            return None

    def _get_output_address(self, label: str) -> int | None:
        """Get coil address by output label."""
        for addr_str, lbl in self.output_map["labels"].items():
            if lbl == label:
                return int(addr_str)
        logger.error(f"Output label '{label}' not found in configuration.")
        return None

    def _get_label_by_address(self, address: int) -> str | None:
        """Get label by coil address."""
        for addr_str, lbl in self.output_map["labels"].items():
            if int(addr_str) == address:
                return lbl
        return None

    def write_output_by_label(self, target_label: str, state: bool) -> bool:
        """Finds physical coil address by label and sends write command."""
        slave_id = self.conn["ouputs_id"]

        target_address = self._get_output_address(target_label)
        if target_address is None:
            return False

        try:
            logger.info(f"Controlling output: {target_label} (Coil {target_address}) -> {'ON' if state else 'OFF'}")
            response = self.client.write_coil(
                address=target_address,
                value=state,
                device_id=slave_id
            )

            if response.isError():
                logger.error(f"Modbus write error for output (Slave {slave_id}, Coil {target_address}): {response}")
                return False
            return True

        except ModbusException as e:
            logger.error(f"Modbus exception while writing output: {e}")
            return False

    def write_outputs_by_labels(self, labels: list[str], state: bool) -> dict[str, bool]:
        """Write multiple outputs by labels. Returns dict of label -> success status."""
        results = {}
        for label in labels:
            success = self.write_output_by_label(label, state)
            results[label] = success
        return results

    def write_outputs_by_bit_numbers(self, bit_numbers: list[int], state: bool) -> dict[str, bool]:
        """Write multiple outputs by coil addresses. Returns dict of label -> success status."""
        results = {}
        for addr in bit_numbers:
            label = self._get_label_by_address(addr)
            if label is None:
                logger.error(f"Coil address {addr} not found in configuration.")
                results[str(addr)] = False
            else:
                success = self.write_output_by_label(label, state)
                results[label] = success
        return results

    def write_coils(self, addresses: list[int], state: bool) -> bool:
        """Write multiple coils in a single Modbus request.

        Coil addresses may be non-contiguous (e.g. 5, 6, 9 or 9, 88),
        but Write Multiple Coils (0x10) only spans a contiguous range.
        So the current state of the whole [min..max] range is read first,
        only the requested coils are updated in that snapshot, and the
        full range is written back with one request. Other coils keep
        their current state.
        """
        slave_id = self.conn["ouputs_id"]
        addresses = sorted(set(addresses))

        start_address = min(addresses)
        count = max(addresses) - start_address + 1

        try:
            # Read current state of the full range
            read_response = self.client.read_coils(
                address=start_address,
                count=count,
                device_id=slave_id
            )

            if read_response.isError():
                logger.error(f"Modbus read coils error (Slave {slave_id}): {read_response}")
                return False

            values = list(read_response.bits)
            for addr in addresses:
                values[addr - start_address] = state

            logger.info(f"Writing {len(addresses)} coil(s) to {'ON' if state else 'OFF'}: {addresses}")
            response = self.client.write_coils(
                address=start_address,
                values=values,
                device_id=slave_id
            )

            if response.isError():
                logger.error(f"Modbus write coils error (Slave {slave_id}): {response}")
                return False
            return True

        except ModbusException as e:
            logger.error(f"Modbus exception while writing coils: {e}")
            return False


if __name__ == "__main__":
    # Demo cycle to check testbench
    tb = IOController()

    if tb.connect():
        try:
            # 1. Read and map inputs
            print("\n=== PLC Button and Output Status ===")
            states = tb.read_inputs()
            if states:
                for label, is_active in states.items():
                    print(f" {label.ljust(15)} : {'[ POWER / SIGNAL ]' if is_active else '[ OFF ]'}")

            print("\n=== Testbench Switching Test ===")
            # 2. Turn on PLC power and enable USB hub channels
            tb.write_output_by_label("USB_EMPTY", True)


        except KeyboardInterrupt:
            logger.info("Execution interrupted by user.")
        finally:
            tb.close()