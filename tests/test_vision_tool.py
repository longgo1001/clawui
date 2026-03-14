#!/usr/bin/env python3
"""Test suite for vision_find_element tool."""

from src.agent import create_tools, execute_tool


def test_vision_tool_registered():
    """Test that vision_find_element tool is registered in agent."""
    tools = create_tools()
    vision_tool_names = [t['name'] for t in tools if 'vision' in t['name']]
    print(f"Vision-related tools found: {vision_tool_names}")

    assert 'vision_find_element' in vision_tool_names, "vision_find_element tool NOT found"
    print("✅ vision_find_element tool registered")


def test_vision_tool_execution():
    """Test that vision_find_element tool can be called."""
    print("Testing vision_find_element tool execution...")

    # Call with missing parameter
    result = execute_tool("vision_find_element", {})
    assert "Missing 'description' parameter" in result.get("text", ""), (
        f"Unexpected result for missing param: {result}"
    )
    print("✅ Missing parameter error handled correctly")

    # Call with description (may fail if vision backend unavailable, but should not crash)
    result = execute_tool("vision_find_element", {"description": "test button"})
    text = result.get("text", "")
    assert isinstance(text, str), f"Unexpected response shape: {result}"
    print("✅ vision_find_element executed without crash")


def main():
    test_vision_tool_registered()
    test_vision_tool_execution()
    print("All tests passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
