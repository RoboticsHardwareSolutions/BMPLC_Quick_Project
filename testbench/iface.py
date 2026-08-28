import logging
import os
import sys

# Built-in TOML parser support
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class IfaceScanner:
    """Scans all [iface.*] devices from testbench.toml and reports undetected ones."""

    def __init__(self, config_path="testbench.toml"):
        # Load configuration from file
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        self.iface_config = config.get("iface", {})
        if not self.iface_config:
            logger.warning(f"No [iface] section found in {config_path}")

    def _is_detected(self, port: str) -> bool:
        """Check if the serial device node exists on the system."""
        return os.path.exists(port)

    def scan(self) -> dict[str, bool]:
        """Check all iface devices. Returns {device_name: detected}."""
        results = {}
        for name, settings in self.iface_config.items():
            port = settings.get("port")
            if not port:
                logger.warning(f"iface.{name}: no 'port' defined, skipping")
                continue
            results[name] = self._is_detected(port)
        return results

    def all_detected(self) -> bool:
        """Return True if all configured iface devices are detected, False otherwise."""
        results = self.scan()
        return bool(results) and all(results.values())

    def report_missing(self) -> list[str]:
        """Scan all devices, print status of each and return names of undetected ones."""
        results = self.scan()

        print("\n=== Iface Device Scan ===")
        for name, detected in results.items():
            port = self.iface_config[name].get("port", "?")
            status = "[ FOUND ]" if detected else "[ NOT DETECTED ]"
            print(f" {name.ljust(10)} : {port}  {status}")

        missing = [name for name, detected in results.items() if not detected]
        if missing:
            print(f"\n{len(missing)} device(s) not detected: {', '.join(missing)}")
        else:
            print("\nAll iface devices detected.")

        return missing


if __name__ == "__main__":
    scanner = IfaceScanner()
    missing = scanner.report_missing()
    print(f"\nAll iface devices detected: {scanner.all_detected()}")
    sys.exit(1 if missing else 0)