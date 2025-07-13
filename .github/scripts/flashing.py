import sys, os

import pylink
from pylink import JLink
import time
import re
from dataclasses import dataclass


@dataclass
class Command:
    command: str
    executed: bool = False


command_map = {
    7.0: Command("?"),
}


def remove_ansi_colors(text: str) -> str:
    """Remove ANSI color codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def run_tests_by_rtt(jlink: JLink, command_map: dict, duration: float = 0.0) -> None:

    try:
        jlink.rtt_start()
        time.sleep(0.1)

        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if duration > 0.0 and elapsed >= duration:
                break

            for cmd_time, cmd_data in command_map.items():
                if not cmd_data.executed and elapsed >= cmd_time:
                    try:
                        jlink.rtt_write(0, cmd_data.command.encode("utf-8"))
                        print(f"Sent at {elapsed:.2f}s: {cmd_data.command}")
                    except Exception as e:
                        print(f"Failed to send command: {cmd_data.command} ({e})")
                    finally:
                        cmd_data.executed = True

            data = jlink.rtt_read(0, 1024)
            if data:
                text = remove_ansi_colors(bytes(data).decode("utf-8", errors="ignore"))
                # Find commands ending with '_test'
                test_commands = [line.strip() for line in text.splitlines() if line.strip().endswith('_test')]

                for test_cmd in test_commands:
                    # Send test command
                    try:
                        jlink.rtt_write(0, test_cmd.encode("utf-8"))
                        print(f"Sent test command: {test_cmd}")
                        time.sleep(0.2)  # Wait for response
                        response = jlink.rtt_read(0, 1024)
                        if response:
                            resp_text = remove_ansi_colors(bytes(response).decode("utf-8", errors="ignore"))
                            # Extract report info
                            match = re.search(
                                r'REPORT\s*\|\s*File:\s*(.*?)\s*\|\s*Test case:\s*(.*?)\s*\|\s*Passes:\s*(\d+)\s*\|\s*Failures:\s*(\d+)',
                                resp_text
                            )
                            if match:
                                file_path = match.group(1)
                                test_case = match.group(2)
                                passed = match.group(3)
                                failed = match.group(4)
                                print(f"Test result for {test_cmd}: {passed} passed, {failed} failed (File: {file_path}, Test case: {test_case})")
                            else:
                                print(f"::warning::No test report found for {test_cmd}. Output:\n{resp_text}")
                    except Exception as e:
                        print(f"Error sending test command {test_cmd}: {e}")
    except Exception as e:
        print(f"Error RTT: {e}")
    finally:
        jlink.rtt_stop()

def flash_device_by_usb(jlink_serial: int, fw_file: str) -> None:
    jlink = pylink.JLink()
    jlink.open(serial_no=jlink_serial)

    if jlink.opened():
        jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
        jlink.connect('STM32F103RE')
        print(jlink.flash_file(fw_file, 0x08000000))
        jlink.reset(halt=False)

        run_tests_by_rtt(jlink, command_map, 10.0)

    jlink.close()

def get_arg() -> str:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        raise ValueError("Путь к файлу не указан или пуст.")

    return os.path.abspath(sys.argv[1].strip())

def main():
    try:
        fw_file = get_arg()
        flash_device_by_usb(771850347, fw_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
