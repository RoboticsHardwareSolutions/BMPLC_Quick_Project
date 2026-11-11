"""Host test of usb_bridge, RS232 target in App mode (../target/usb_bridge_echo.c, `usb_bridge_echo rs232`).

App mode does not touch the UART, so this also runs on boards without rhs_hal_serial (G0B1).
The echo application returns every byte from the host from its callback (direct path); `usb_bridge_echo burst <n>`
sends n counter bytes from the CLI thread (queue path). Needs the board and the J-Link, see usb_bridge_hw.py.
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Iterator

import pytest

import usb_bridge_hw as hw

serial = pytest.importorskip("serial")

pytestmark = hw.requires_hw

RX_TIMEOUT_S = 2.0


@pytest.fixture(scope="module", autouse=True)
def echo_rs232(plc) -> Iterator[None]:
    hw.echo_start(plc, "rs232")
    yield
    hw.echo_stop(plc)


@pytest.fixture
def port() -> Iterator["serial.Serial"]:
    ser = serial.Serial(hw.PORT, 9600, timeout=0.05)
    ser.reset_input_buffer()
    try:
        yield ser
    finally:
        ser.close()


def read_exactly(ser, count: int, timeout: float) -> bytes:
    data = bytearray()
    deadline = time.monotonic() + timeout
    while len(data) < count and time.monotonic() < deadline:
        data += ser.read(count - len(data))
    return bytes(data)


def counter(count: int) -> bytes:
    return bytes(i & 0xFF for i in range(count))


# ------------------------------------------------------------------ 1. echo


@pytest.mark.parametrize("size", [1, 64, 65, 1000])
def test_echo(port, size: int) -> None:
    data = os.urandom(size)
    port.write(data)
    assert read_exactly(port, size, RX_TIMEOUT_S) == data


def test_echo_all_byte_values(port) -> None:
    data = bytes(range(256)) * 4  # incl. 0x00, CR, LF, XON/XOFF: no line discipline on the device
    port.write(data)
    assert read_exactly(port, len(data), RX_TIMEOUT_S) == data


# ------------------------------------------------------------------ 2. stream


def test_stream_64k(port) -> None:
    """64 KB written while reading back concurrently: nothing lost, order kept."""
    data = os.urandom(64 * 1024)
    received = bytearray()

    def reader() -> None:
        deadline = time.monotonic() + 30.0
        while len(received) < len(data) and time.monotonic() < deadline:
            received.extend(port.read(4096))

    thread = threading.Thread(target=reader)
    thread.start()
    for i in range(0, len(data), 512):
        port.write(data[i : i + 512])
    thread.join()
    assert len(received) == len(data)
    assert bytes(received) == data


# ------------------------------------------------------------------ 3. burst from another thread


@pytest.mark.parametrize("count", [1, 1000, 20000])
def test_burst_from_cli_thread(plc, port, count: int) -> None:
    received = bytearray()

    def reader() -> None:
        deadline = time.monotonic() + 10.0 + count / 1000
        while len(received) < count and time.monotonic() < deadline:
            received.extend(port.read(4096))

    thread = threading.Thread(target=reader)
    thread.start()
    out = plc.run_until(f"usb_bridge_echo burst {count}", f"sent {count}", timeout=10.0 + count / 1000)
    thread.join()
    assert f"sent {count}" in out, out
    assert bytes(received) == counter(count)
    assert read_exactly(port, 1, 0.3) == b"", "more bytes than requested"


# ------------------------------------------------------------------ 4. baudrate from the host


def test_host_baudrate_change(plc, port) -> None:
    port.baudrate = 115200
    time.sleep(0.2)
    port.write(b"after baud change")
    assert read_exactly(port, 17, RX_TIMEOUT_S) == b"after baud change"
    state = plc.run_until("usb_bridge_echo state", "baudrate")
    assert re.search(r"baudrate: 115200\b", state), state
    assert re.search(r"open: 1\b", state), state  # pyserial raises DTR


# ------------------------------------------------------------------ 5. one bridge at a time


def test_second_bridge_refused(plc, port) -> None:
    out = plc.run_until("usb can bridge", "error")
    assert "error" in out, out
    assert "stopped" in plc.run_until("usb state", "stopped")
    port.write(b"still echo")
    assert read_exactly(port, 10, RX_TIMEOUT_S) == b"still echo"


# ------------------------------------------------------------------ 6. stop and switch target


def test_stop_and_switch_target(plc) -> None:
    hw.echo_stop(plc)  # port disappears
    hw.echo_start(plc, "can")
    with serial.Serial(hw.PORT, 115200, timeout=0.5) as ser:
        ser.write(b"V\r")
        assert ser.read(6) == b"V1010\r", "CAN target does not answer SLCAN"
    hw.echo_stop(plc)
    hw.echo_start(plc, "rs485")
    with serial.Serial(hw.PORT, 9600, timeout=0.05) as ser:
        ser.write(b"rs485")
        assert read_exactly(ser, 5, RX_TIMEOUT_S) == b"rs485"
    hw.echo_stop(plc)
    hw.echo_start(plc, "rs232")  # back for the module fixture teardown
