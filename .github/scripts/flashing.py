import sys, os

import pylink
from pylink import JLink


def flash_device_by_usb(jlink_serial: int, fw_file: str) -> None:
    jlink = pylink.JLink()
    jlink.open(serial_no=jlink_serial)

    if jlink.opened():
        jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
        jlink.connect('STM32F103RE')
        print(jlink.flash_file(fw_file, 0x08000000))
        jlink.reset(halt=False)

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
