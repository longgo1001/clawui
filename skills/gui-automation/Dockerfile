# ClawUI - AI-driven Linux GUI automation
# Provides a headless environment with AT-SPI, xdotool, and virtual display
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
    XDG_RUNTIME_DIR=/run/user/1000 \
    LANG=C.UTF-8

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-gi python3-gi-cairo \
    gir1.2-atspi-2.0 libgirepository1.0-dev gobject-introspection \
    xdotool xvfb dbus-x11 at-spi2-core \
    tesseract-ocr gnome-screenshot \
    fonts-dejavu-core \
    xterm \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 clawui && \
    mkdir -p /run/user/1000 && \
    chown clawui:clawui /run/user/1000

WORKDIR /app
COPY requirements.txt pyproject.toml ./
COPY src/ src/
COPY tests/ tests/

# Install Python deps
RUN pip install --no-cache-dir --break-system-packages -e ".[dev]" && \
    pip install --no-cache-dir --break-system-packages pytest pytest-timeout

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER clawui
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["pytest", "tests/", "-v", "--timeout=120"]
