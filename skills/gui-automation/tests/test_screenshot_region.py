import base64
import io

from PIL import Image


def test_region_capture_x11_does_not_recrop(monkeypatch):
    from clawui import screenshot as mod

    monkeypatch.setattr(mod, "_get_session_type", lambda: "x11")

    def fake_which(cmd):
        return "/usr/bin/scrot" if cmd == "scrot" else None

    monkeypatch.setattr(mod.shutil, "which", fake_which)

    def fake_run(cmd, **kwargs):
        if cmd[0] == "scrot" and "-a" in cmd:
            out = cmd[-1]
            Image.new("RGB", (80, 60), "blue").save(out)
            class R:
                returncode = 0
            return R()
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    b64 = mod.take_screenshot(region=(10, 10, 80, 60), scale=False)
    data = base64.b64decode(b64)
    img = Image.open(io.BytesIO(data))
    assert img.size == (80, 60)
    # If an incorrect second crop happened, bottom-right often becomes padded black.
    assert img.getpixel((79, 59)) == (0, 0, 255)


def test_region_capture_wayland_crops_fullscreen(monkeypatch):
    from clawui import screenshot as mod

    monkeypatch.setattr(mod, "_get_session_type", lambda: "wayland")

    def fake_which(cmd):
        return "/usr/bin/gnome-screenshot" if cmd == "gnome-screenshot" else None

    monkeypatch.setattr(mod.shutil, "which", fake_which)

    def fake_dbus_env():
        return {}

    monkeypatch.setattr(mod, "_dbus_env", fake_dbus_env)

    def fake_run(cmd, **kwargs):
        if cmd[0] == "gnome-screenshot":
            out = cmd[-1]
            Image.new("RGB", (200, 150), "green").save(out)
            class R:
                returncode = 0
            return R()
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    b64 = mod.take_screenshot(region=(20, 30, 50, 40), scale=False)
    data = base64.b64decode(b64)
    img = Image.open(io.BytesIO(data))
    assert img.size == (50, 40)
