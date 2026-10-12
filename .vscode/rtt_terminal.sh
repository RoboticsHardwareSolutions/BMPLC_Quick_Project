#!/usr/bin/env bash
# Universal RTT/log terminal for BlackMagic Probe.
#
#   TCP : host:port                     (telnet to BMP over network)
#   VCP : /dev/cu.usbmodemXXXX3         (serial; optional baud via '@',
#         e.g. /dev/cu.usbmodemXXXX3@921600, default 115200)
set -u

TARGET="${1:-}"
BAUD="115200"

if [[ -z "$TARGET" ]]; then
    echo "rtt_terminal: no target specified" >&2
    exit 1
fi

# ---------- TCP (telnet) ----------
if [[ "$TARGET" == *:* ]]; then
    HOST="${TARGET%:*}"
    PORT="${TARGET##*:}"
    echo "RTT: connecting to TCP $HOST:$PORT (Ctrl-C to stop)..."
    exec nc "$HOST" "$PORT"
fi

# ---------- Serial VCP ----------
DEV="${TARGET%%@*}"
if [[ "$TARGET" == *@* ]]; then
    BAUD="${TARGET##*@}"
fi

# macOS termios has no B921600/B1000000 - socat rejects such b<N> options.
case "$BAUD" in
    1200|2400|4800|9600|19200|38400|57600|115200|230400) ;;
    *)
        echo "RTT: baud '$BAUD' not supported by macOS, using 115200" >&2
        BAUD="115200"
        ;;
esac

# Allow short names: "usbmodemXXXX3" -> /dev/cu.usbmodemXXXX3
if [[ "$DEV" != /dev/* ]]; then
    if [[ -c "/dev/cu.$DEV" ]]; then
        DEV="/dev/cu.$DEV"
    elif [[ -c "/dev/$DEV" ]]; then
        DEV="/dev/$DEV"
    fi
fi

# tty.* devices are lock-prone; always prefer the cu.* twin
if [[ "$DEV" == /dev/tty.* ]]; then
    DEV="/dev/cu.${DEV#/dev/tty.}"
    echo "RTT: note - using $DEV instead of tty.*"
fi

if [[ ! -c "$DEV" ]]; then
    echo "RTT: device '$DEV' not found. Available serial devices:" >&2
    ls /dev/cu.* 2>/dev/null | grep -iv bluetooth | sed 's/^/RTT:   /' >&2
    echo "RTT: hint - BMP GDB port usually ends in 1, UART/VCP port ends in 3" >&2
    exit 1
fi

echo "RTT: connecting to VCP $DEV @ $BAUD (Ctrl-C to stop)..."
if command -v socat >/dev/null 2>&1; then
    # socat: no lock files, clean exit, raw mode.
    # NOTE: this socat build (1.8.1.1) mis-parses b<N>; use ispeed/ospeed.
    exec socat - "$DEV,raw,echo=0,ispeed=$BAUD,ospeed=$BAUD"
fi
# Fallback: macOS screen
exec /usr/bin/screen "$DEV" "$BAUD"
