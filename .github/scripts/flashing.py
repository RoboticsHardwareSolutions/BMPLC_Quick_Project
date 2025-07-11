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


def read_rtt_to_file(jlink: JLink, command_map: dict, duration: float = 0.0) -> None:
    filename = f"artefacts/rtt_log_{time.strftime('%Y%m%d_%H%M%S')}.txt"

    try:
        jlink.rtt_start()
        time.sleep(0.1)

        with open(filename, "w") as f:
            start_time = time.time()
            while time.time() - start_time < duration or duration == 0.0:

                current_time = time.time() - start_time
                for cmd_time, cmd_data in command_map.items():
                    if not cmd_data.executed and current_time >= cmd_time:
                        try:
                            jlink.rtt_write(0, cmd_data.command.encode("utf-8"))
                            print(f"Sent at {current_time:.2f}s: {cmd_data.command}")
                            cmd_data.executed = True
                        except Exception as e:
                            print(f"Failed to send command: {cmd_data.command}")
                            cmd_data.executed = True

                data = jlink.rtt_read(0, 1024)
                if data:
                    text = remove_ansi_colors(
                        bytes(data).decode("utf-8", errors="ignore")
                    )
                    print(f"len={len(data)}")
                    f.write(text)
                    f.flush()

    except Exception as e:
        print(f"Error RTT: {e}")
    finally:
        jlink.rtt_stop()

def flash_device_by_usb(jlink: JLink, fw_file: str) -> None:
    if not jlink.opened():
        print("JLink not open")
        return

    try:
        jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
        jlink.connect("STM32F103RE")
        result = jlink.flash_file(fw_file, 0x08000000)
        print(f"Flash result: {result}")
        jlink.reset(halt=False)
    except Exception as e:
        print(f"Error flashing device: {e}")

def get_arg() -> str:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        raise ValueError("Путь к файлу не указан или пуст.")

    return os.path.abspath(sys.argv[1].strip())

def main():
    fw_file = get_arg()

    with pylink.JLink() as jlink:
        jlink.open(serial_no=771850347)
        flash_device_by_usb(jlink, fw_file)
        read_rtt_to_file(jlink, command_map, 10.0)
        jlink.close()

if __name__ == "__main__":
    main()
