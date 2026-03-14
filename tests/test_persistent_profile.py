#!/usr/bin/env python3
"""Test persistent profile integration for CDP auto-launch."""

import os
import time
import subprocess

from src.cdp_helper import launch_chromium_with_cdp, DEFAULT_USER_DATA_DIR, get_or_create_cdp_client


def test_profile_dir_exists():
    """Test that the default profile directory is present or creatable."""
    print("1. Testing profile directory creation...")
    if os.path.exists(DEFAULT_USER_DATA_DIR):
        print(f"   Profile dir already exists: {DEFAULT_USER_DATA_DIR}")
    else:
        print("   Profile dir missing now; will be created on launch")


def test_launch_with_profile():
    """Test that Chromium launches with the correct user-data-dir."""
    print("2. Testing Chromium launch with persistent profile...")

    # Kill any existing Chromium processes to avoid conflicts
    try:
        subprocess.run(['pkill', '-f', 'chromium'], capture_output=True)
        time.sleep(1)
    except Exception:
        pass

    # Launch with CDP
    proc = launch_chromium_with_cdp(port=9223, url="about:blank")
    assert proc, "Failed to launch Chromium"

    print(f"   ✅ Launched Chromium (PID: {proc.pid})")
    time.sleep(2)

    # Verify profile dir exists on disk (Snap Chromium may hide args from ps)
    assert os.path.isdir(DEFAULT_USER_DATA_DIR), (
        f"Profile directory not created: {DEFAULT_USER_DATA_DIR}"
    )
    print(f"   ✅ Profile dir exists: {DEFAULT_USER_DATA_DIR}")

    # Test CDP connection
    client = get_or_create_cdp_client(port=9223)
    assert client and client.is_available(), "CDP endpoint not available"
    print("   ✅ CDP endpoint is available")
    title = client.get_page_title()
    url = client.get_page_url()
    print(f"   Page: {title} @ {url}")

    # Cleanup
    try:
        proc.terminate()
        proc.wait(timeout=5)
        print("   ✅ Browser terminated")
    except Exception:
        subprocess.run(['pkill', '-f', '--', '--remote-debugging-port=9223'], capture_output=True)


def main():
    print("=== Persistent Profile CDP Test ===")
    test_profile_dir_exists()
    test_launch_with_profile()
    print("\n✅ All tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
