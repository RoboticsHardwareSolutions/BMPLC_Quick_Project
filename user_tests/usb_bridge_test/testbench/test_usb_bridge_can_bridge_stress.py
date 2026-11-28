"""HIL stress/characterization tests for usb_bridge's CAN Bridge mode on BMPLC_XL -- an EMPIRICAL assessment
of the SLCAN bridge path's real capabilities (throughput, burst capacity, latency), not a theoretical
calculation. See test_usb_bridge_can_bridge.py for the fixture/hardware-precondition background shared here.

These are characterization tests, not pure correctness tests: each measurement prints a human-readable
finding via `print()` (run with `-s` to see it) and additionally asserts a generous, documented lower-bound
threshold -- tight enough to catch a severe regression (e.g. throughput silently halved by a future firmware
change), loose enough that normal USB-stack/host-scheduling jitter never makes this flaky. The interesting
output is the printed numbers, not just PASSED/FAILED.

Why the real bottleneck is almost certainly NOT the CAN bus itself: a standard CAN frame is ~108-128 bits
even at 500 kbit/s (~0.2-0.25 ms), while each SLCAN ASCII line is ~10-20 bytes sent over TWO independent
USB-CDC hops (the PLC's own CDC port, and the bench's [iface.canbus] adapter's CDC port) plus whatever the
firmware's CDC<->CAN forwarding loop costs per frame. The throughput-across-bitrates measurement below exists
specifically to check this empirically: if frames/s stays flat across very different CAN bitrates, the
serial/firmware path is the ceiling, not the physical bus.
"""

from __future__ import annotations

import os
import statistics
import time
from typing import Iterator

import pytest

import usb_bridge_hw as hw

can = pytest.importorskip("can")

pytestmark = pytest.mark.skipif(
    os.environ.get("PLC_TYPE") != "BMPLC_XL",
    reason="CAN Bridge E2E needs the HIL stand's [iface.canbus] adapter; BMPLC_XL only -- "
    "BMPLC_M rejects CAN Bridge (see test_usb_bridge_cli.py)",
)

BITRATE = 500000
RX_TIMEOUT_S = 1.0


@pytest.fixture(scope="module")
def canbus_port(tb_client) -> str:
    path = hw.canbus_port(tb_client)
    if path is None:
        pytest.skip("bench [iface.canbus] adapter not present")
    return path


@pytest.fixture
def canbus_bus(canbus_port: str) -> Iterator[can.BusABC]:
    b = can.Bus(interface="slcan", channel=canbus_port, bitrate=BITRATE, sleep_after_open=0.2)
    try:
        hw.recv_frames(b, 1000, 0.2)
        yield b
    finally:
        b.shutdown()


@pytest.fixture(scope="module", autouse=True)
def bridge_can(plc, io_config, request: pytest.FixtureRequest) -> Iterator[None]:
    hw.bridge_start(plc, "bridge", io_config, request)
    yield
    hw.bridge_stop(plc, io_config, request)


@pytest.fixture
def plc_bus() -> Iterator[can.BusABC]:
    b = can.Bus(interface="slcan", channel=hw.PORT, bitrate=BITRATE, sleep_after_open=0.2)
    try:
        hw.recv_frames(b, 1000, 0.2)
        yield b
    finally:
        b.shutdown()


# ------------------------------------------------------------------ (a) sustained throughput without loss


def _run_throughput(plc_bus: "can.BusABC", canbus_bus: "can.BusABC", count: int) -> tuple[int, int, float]:
    """Send `count` frames back to back in each direction (no pacing -- the point is to find the real
    ceiling, not stay safely under it), return (delivered_to_device, delivered_to_usb, elapsed_s)."""
    sent_to_device = [can.Message(arbitration_id=0x300 + (i % 0x400), data=(i & 0xFFFF).to_bytes(2, "big"), is_extended_id=False) for i in range(count)]
    sent_to_usb = [can.Message(arbitration_id=0x500 + (i % 0x400), data=(i & 0xFFFF).to_bytes(2, "big"), is_extended_id=False) for i in range(count)]

    t0 = time.monotonic()
    for a, b in zip(sent_to_device, sent_to_usb):
        plc_bus.send(a)
        canbus_bus.send(b)

    got_on_device = hw.recv_frames(canbus_bus, count, timeout=10.0 + count / 50)
    got_on_usb = hw.recv_frames(plc_bus, count, timeout=10.0 + count / 50)
    elapsed = time.monotonic() - t0

    return len(got_on_device), len(got_on_usb), elapsed


def test_throughput_default_bitrate(plc, plc_bus: "can.BusABC", canbus_bus: "can.BusABC") -> None:
    """Primary throughput measurement at the suite's default bitrate (500000) -- this is the one with a
    real (generous) floor assertion; the cross-bitrate comparison below is purely informational."""
    count = 200
    delivered_device, delivered_usb, elapsed = _run_throughput(plc_bus, canbus_bus, count)

    fps_device = delivered_device / elapsed
    fps_usb = delivered_usb / elapsed
    print(
        f"\n[throughput @ {BITRATE} bps] sent {count} each way in {elapsed:.3f}s: "
        f"usb->device {delivered_device}/{count} delivered ({fps_device:.0f} fps), "
        f"device->usb {delivered_usb}/{count} delivered ({fps_usb:.0f} fps)"
    )

    state = plc.run_until("usb state", "app rx")
    print(f"[usb state after burst]\n{state.strip()}")

    # Generous floor: catches a severe regression (e.g. throughput silently halved), not a tight target.
    assert fps_device > 50, f"usb->device throughput collapsed: {fps_device:.0f} fps"
    assert fps_usb > 50, f"device->usb throughput collapsed: {fps_usb:.0f} fps"


def test_throughput_across_bitrates(plc, io_config, request: pytest.FixtureRequest, canbus_port: str) -> None:
    """Informational only: does achieved throughput scale with the CAN bus bitrate, or stay flat? Flat
    across very different bitrates means the SLCAN/serial/firmware path is the real ceiling, not the
    physical bus -- that conclusion is the actual deliverable of this test, printed for a human to read.

    Manages its own bridge lifecycle independently of the module's `bridge_can` fixture (stops the
    500000-bps bridge that fixture started, cycles through its own bitrates, restarts the default bridge at
    the end so the module fixture's teardown -- which just runs `usb stop` once more -- has a live bridge to
    stop). Keep this the LAST test in the file for that reason.
    """
    count = 100
    results: list[tuple[int, float, float]] = []

    hw.bridge_stop(plc, io_config, request)
    for bitrate in (125000, 500000, 1000000):
        hw.bridge_start(plc, "bridge", io_config, request, baud=bitrate)
        try:
            plc_bus = can.Bus(interface="slcan", channel=hw.PORT, bitrate=bitrate, sleep_after_open=0.2)
            canbus_bus = can.Bus(
                interface="slcan", channel=canbus_port, bitrate=bitrate, sleep_after_open=0.2
            )
            try:
                hw.recv_frames(plc_bus, 1000, 0.2)
                hw.recv_frames(canbus_bus, 1000, 0.2)
                delivered_device, delivered_usb, elapsed = _run_throughput(plc_bus, canbus_bus, count)
                results.append((bitrate, delivered_device / elapsed, delivered_usb / elapsed))
            finally:
                plc_bus.shutdown()
                canbus_bus.shutdown()
        finally:
            hw.bridge_stop(plc, io_config, request)
    hw.bridge_start(plc, "bridge", io_config, request)  # leave a bridge running for the module fixture to tear down

    print("\n[throughput vs CAN bitrate] (usb->device fps, device->usb fps):")
    for bitrate, fps_device, fps_usb in results:
        print(f"  {bitrate:>8} bps: {fps_device:6.0f} fps / {fps_usb:6.0f} fps")
    spread = max(r[1] for r in results) - min(r[1] for r in results)
    flat = spread < min(r[1] for r in results)  # spread smaller than the slowest result itself -- informational only
    print(f"[conclusion] throughput is {'roughly flat' if flat else 'scaling'} across bitrates -> "
          f"the {'serial/firmware path' if flat else 'CAN bus bitrate'} looks like the real ceiling")


# ------------------------------------------------------------------ (b) burst-size breaking point


@pytest.mark.parametrize("count", [10, 50, 100, 500, 1000, 2000, 5000])
def test_burst_breaking_point(plc_bus: "can.BusABC", canbus_bus: "can.BusABC", count: int) -> None:
    """One-directional (usb->device) escalating burst, no inter-frame pacing. Sizes <=100 are a correctness
    floor (must always arrive 100% intact, in order) -- above that this only reports the delivery
    percentage and whether order was preserved, since partial loss under extreme, unpaced load is the
    expected finding here, not a bug."""
    sent = [can.Message(arbitration_id=0x100 + (i % 0x400), data=(i & 0xFFFF).to_bytes(2, "big"), is_extended_id=False) for i in range(count)]

    t0 = time.monotonic()
    for msg in sent:
        plc_bus.send(msg)
    got = hw.recv_frames(canbus_bus, count, timeout=5.0 + count / 50)
    elapsed = time.monotonic() - t0

    got_ids = [f.arbitration_id for f in got]
    sent_ids = [m.arbitration_id for m in sent]
    in_order = got_ids == sent_ids[: len(got_ids)]
    pct = 100.0 * len(got) / count

    print(f"\n[burst {count}] delivered {len(got)}/{count} ({pct:.1f}%) in {elapsed:.3f}s, in_order={in_order}")

    if count <= 100:
        assert len(got) == count, f"burst of {count} must arrive intact, got {len(got)}/{count}"
        assert in_order, f"burst of {count} must arrive in order"
    else:
        assert len(got) > 0, f"nothing arrived at all for a burst of {count}"
        assert in_order, "frames that did arrive must still be in order (partial loss is OK, reordering is not)"


# ------------------------------------------------------------------ (c) per-frame latency distribution


def _measure_latency(sender: "can.BusABC", receiver: "can.BusABC", samples: int) -> list[float]:
    """Host-side time.monotonic() bracketing around one send + the matching recv -- NOT a diff of
    Message.timestamp between `sender`/`receiver`: those are two independent serial connections with no
    shared clock, so a cross-object timestamp diff isn't meaningful. One frame at a time with a settle gap,
    matched by a unique arbitration ID per sample, so this measures real send-call-to-recv-return latency
    through the full pipeline, not throughput (that's (a)'s job)."""
    latencies: list[float] = []
    for i in range(samples):
        can_id = 0x600 + (i % 0x200)
        t0 = time.monotonic()
        sender.send(can.Message(arbitration_id=can_id, data=[i & 0xFF], is_extended_id=False))
        deadline = t0 + 2.0
        while time.monotonic() < deadline:
            frame = receiver.recv(0.1)
            if frame is not None and frame.arbitration_id == can_id:
                latencies.append(time.monotonic() - t0)
                break
        time.sleep(0.05)  # settle gap: measuring latency, not throughput
    return latencies


def _report_latency(label: str, latencies: list[float]) -> None:
    assert latencies, f"{label}: no samples arrived at all"
    s = sorted(latencies)
    p95 = s[int(0.95 * (len(s) - 1))]
    print(
        f"\n[latency {label}] n={len(s)} min={s[0] * 1000:.1f}ms median={statistics.median(s) * 1000:.1f}ms "
        f"p95={p95 * 1000:.1f}ms max={s[-1] * 1000:.1f}ms"
    )
    # Generous sanity ceiling, not a tight target -- each SLCAN line is a full ASCII round-trip over two
    # independent USB-CDC hops (PLC's own CDC + the bench adapter's CDC) plus the firmware's forwarding loop.
    assert statistics.median(s) < 0.1, f"{label}: median latency {statistics.median(s) * 1000:.1f}ms exceeds the 100ms sanity ceiling"


def test_latency_usb_to_device(plc_bus: "can.BusABC", canbus_bus: "can.BusABC") -> None:
    _report_latency("usb->device", _measure_latency(plc_bus, canbus_bus, samples=50))


def test_latency_device_to_usb(plc_bus: "can.BusABC", canbus_bus: "can.BusABC") -> None:
    _report_latency("device->usb", _measure_latency(canbus_bus, plc_bus, samples=50))
