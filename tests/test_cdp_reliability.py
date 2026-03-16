#!/usr/bin/env python3
"""Reliability-focused unit tests for CDP transport helpers."""

import json
import os
import sys

# Ensure this repository's clawui package is imported (avoid workspace-global shadowing)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO_ROOT)
sys.modules.pop('clawui', None)


class _FakeWS:
    def __init__(self, responses):
        self._responses = list(responses)
        self.sent = []

    def send(self, payload):
        self.sent.append(json.loads(payload))

    def recv(self):
        if not self._responses:
            raise RuntimeError("no more responses")
        return json.dumps(self._responses.pop(0))

    def close(self):
        return None

    def ping(self):
        return True


def test_send_cdp_command_retries_after_transport_error(monkeypatch):
    from clawui.cdp_helper import CDPClient

    # First WS dies on recv, second WS returns valid response.
    first = _FakeWS([])
    second = _FakeWS([{"id": 2, "result": {"ok": True}}])
    calls = {"n": 0}

    def _create_connection(_url, timeout=10):
        calls["n"] += 1
        return first if calls["n"] == 1 else second

    from types import SimpleNamespace
    monkeypatch.setitem(sys.modules, "websocket", SimpleNamespace(create_connection=_create_connection))

    client = CDPClient(port=19222)
    result = client._send_cdp_command("ws://fake", "Runtime.evaluate", {"expression": "1+1"})

    assert result == {"ok": True}
    assert calls["n"] == 2


def test_dispatch_mouse_reports_failure_when_cdp_returns_none(monkeypatch):
    from clawui.cdp_helper import CDPClient

    client = CDPClient(port=19222)
    # Force _raw_cdp to fail for both pressed/released events.
    monkeypatch.setattr(client, "_raw_cdp", lambda *_args, **_kwargs: None)

    ok = client.dispatch_mouse(100, 200)
    assert ok is False
