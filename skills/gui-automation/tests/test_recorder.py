"""Tests for recorder module: record, save, load, playback, export."""

import json
import os
import tempfile
import time

import pytest

from clawui.recorder import (
    Recorder,
    Player,
    start_recording,
    record_action,
    stop_recording,
    play_recording,
    export_to_script,
)


@pytest.fixture
def tmp_dir(tmp_path):
    return str(tmp_path)


class TestRecorder:
    def test_record_and_save(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.json")
        rec = Recorder(path)
        rec.record("click", {"x": 100, "y": 200}, "ok")
        rec.record("type_text", {"text": "hello"}, "ok")
        saved = rec.save()
        assert saved == path
        assert os.path.exists(path)

        with open(path) as f:
            data = json.load(f)
        assert data["metadata"]["count"] == 2
        assert len(data["actions"]) == 2
        assert data["actions"][0]["tool"] == "click"
        assert data["actions"][1]["input"]["text"] == "hello"

    def test_load(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.json")
        rec = Recorder(path)
        rec.record("screenshot", {})
        rec.save()

        loaded = Recorder.load(path)
        assert len(loaded.actions) == 1
        assert loaded.actions[0]["tool"] == "screenshot"

    def test_timestamps_are_relative(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.json")
        rec = Recorder(path)
        rec.record("click", {"x": 0, "y": 0})
        time.sleep(0.05)
        rec.record("click", {"x": 1, "y": 1})
        rec.save()

        with open(path) as f:
            data = json.load(f)
        t0 = data["actions"][0]["timestamp"]
        t1 = data["actions"][1]["timestamp"]
        assert t0 >= 0
        assert t1 > t0

    def test_default_filepath(self, tmp_dir):
        # Default path includes timestamp
        rec = Recorder()
        assert "recording_" in rec.filepath


class TestPlayer:
    def test_play(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.json")
        rec = Recorder(path)
        rec.record("click", {"x": 10, "y": 20})
        rec.record("type_text", {"text": "hi"})
        rec.save()

        loaded = Recorder.load(path)
        executed = []

        def fake_execute(tool, inp):
            executed.append((tool, inp))
            return "done"

        player = Player(loaded, fake_execute)
        results = player.play(delay=0.01)
        assert len(results) == 2
        assert all(r == "done" for r in results)
        assert executed[0] == ("click", {"x": 10, "y": 20})
        assert executed[1] == ("type_text", {"text": "hi"})

    def test_dry_run(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.json")
        rec = Recorder(path)
        rec.record("click", {"x": 10, "y": 20})
        rec.save()

        loaded = Recorder.load(path)
        executed = []

        def fake_execute(tool, inp):
            executed.append(tool)
            return "done"

        player = Player(loaded, fake_execute)
        results = player.play(delay=0.01, dry_run=True)
        assert len(results) == 1
        assert results[0] is None
        assert len(executed) == 0  # Nothing actually executed


class TestConvenienceWrappers:
    def test_start_stop_recording(self, tmp_dir):
        path = os.path.join(tmp_dir, "wrap.json")
        start_recording(path)
        record_action("click", {"x": 5, "y": 5})
        record_action("press_key", {"key": "Return"})
        saved = stop_recording()
        assert saved == path

        with open(path) as f:
            data = json.load(f)
        assert data["metadata"]["count"] == 2

    def test_stop_without_start(self):
        result = stop_recording()
        assert result is None

    def test_record_without_start(self):
        # Should not raise
        record_action("click", {"x": 0, "y": 0})

    def test_play_recording(self, tmp_dir):
        path = os.path.join(tmp_dir, "play.json")
        rec = Recorder(path)
        rec.record("screenshot", {})
        rec.save()

        calls = []
        results = play_recording(path, lambda t, i: calls.append(t) or "ok", delay=0.01)
        assert len(results) == 1
        assert calls == ["screenshot"]


class TestExportToScript:
    def test_desktop_actions(self, tmp_dir):
        path = os.path.join(tmp_dir, "desktop.json")
        rec = Recorder(path)
        rec.record("click", {"x": 100, "y": 200})
        rec.record("type_text", {"text": "hello"})
        rec.record("press_key", {"key": "Return"})
        rec.save()

        out = export_to_script(path, os.path.join(tmp_dir, "desktop.py"))
        assert os.path.exists(out)
        content = open(out).read()
        assert "click(100, 200)" in content
        assert "type_text('hello')" in content
        assert "press_key('Return')" in content
        assert "import time" in content
        assert "CDPClient" not in content

    def test_cdp_actions(self, tmp_dir):
        path = os.path.join(tmp_dir, "cdp.json")
        rec = Recorder(path)
        rec.record("cdp_navigate", {"url": "https://example.com"})
        rec.record("cdp_click", {"selector": "#btn"})
        rec.save()

        out = export_to_script(path, os.path.join(tmp_dir, "cdp.py"))
        content = open(out).read()
        assert "CDPClient" in content
        assert "cdp.navigate('https://example.com')" in content
        assert "cdp.click('#btn')" in content

    def test_unknown_tool_as_comment(self, tmp_dir):
        path = os.path.join(tmp_dir, "unknown.json")
        rec = Recorder(path)
        rec.record("custom_tool", {"arg": "val"})
        rec.save()

        out = export_to_script(path, os.path.join(tmp_dir, "unknown.py"))
        content = open(out).read()
        assert "# TODO: custom_tool" in content

    def test_executable_permission(self, tmp_dir):
        path = os.path.join(tmp_dir, "exec.json")
        rec = Recorder(path)
        rec.record("screenshot", {})
        rec.save()

        out = export_to_script(path, os.path.join(tmp_dir, "exec.py"))
        assert os.access(out, os.X_OK)

    def test_default_output_name(self, tmp_dir):
        path = os.path.join(tmp_dir, "rec.json")
        rec = Recorder(path)
        rec.record("click", {"x": 0, "y": 0})
        rec.save()

        out = export_to_script(path)
        assert out == path.replace(".json", ".py")
        assert os.path.exists(out)
