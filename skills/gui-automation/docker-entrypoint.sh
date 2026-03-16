#!/bin/bash
set -e

# Start D-Bus session bus
if [ -z "$DBUS_SESSION_BUS_PID" ]; then
    eval "$(dbus-launch --sh-syntax)"
    export DBUS_SESSION_BUS_ADDRESS
fi

# Start AT-SPI registry
/usr/libexec/at-spi2-registryd &>/dev/null &
sleep 0.3

# Start Xvfb (virtual display)
Xvfb :99 -screen 0 1920x1080x24 -ac &>/dev/null &
sleep 0.5

# Launch a simple window so AT-SPI has something to see
if command -v xterm &>/dev/null; then
    xterm -T "ClawUI Test Window" -geometry 80x24+100+100 &
    sleep 0.3
fi

exec "$@"
