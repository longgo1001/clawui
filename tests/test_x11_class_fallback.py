import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch


def _load_repo_x11_helper_module():
    module_path = Path(__file__).resolve().parents[1] / "skills" / "gui-automation" / "src" / "x11_helper.py"
    spec = importlib.util.spec_from_file_location("repo_x11_helper", module_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_x11_window_class_fallback_to_process_for_electron():
    mod = _load_repo_x11_helper_module()

    def _fake_run(cmd, capture_output=True, text=True, timeout=5):
        if cmd[:3] == ["xdotool", "search", "--name"]:
            return MagicMock(returncode=0, stdout="100\n")
        if cmd[:2] == ["xdotool", "getwindowgeometry"]:
            return MagicMock(returncode=0, stdout="Window 100:\n  Position: 10,20 (screen: 0)\n  Geometry: 800x600\n")
        if cmd[:2] == ["xdotool", "getwindowname"]:
            return MagicMock(returncode=0, stdout="My Electron App\n")
        if cmd[:2] == ["xdotool", "getwindowpid"]:
            return MagicMock(returncode=0, stdout="12345\n")
        if cmd[:2] == ["xdotool", "getwindowclassname"]:
            return MagicMock(returncode=0, stdout="\n")
        if cmd[:2] == ["xprop", "-id"]:
            return MagicMock(returncode=0, stdout='WM_CLASS(STRING) = "", ""\n')
        return MagicMock(returncode=0, stdout="")

    with patch.object(mod.subprocess, "run", side_effect=_fake_run), patch.object(
        mod, "_get_process_name", return_value="electron"
    ):
        wins = mod.list_windows()

    assert len(wins) == 1
    assert wins[0].class_name == "electron"
