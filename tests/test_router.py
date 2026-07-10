"""Real tests for MLX tool-calling -- no mocks.

mlx-lm is Keep's optional `[mlx]` extra (see keep.router.mlx_available); the
tests that actually load and run the local model skip cleanly via
pytest.importorskip when it isn't installed, rather than failing.
"""

import subprocess

import pytest


def test_run_mlx_tools_executes_a_real_tool_call():
    pytest.importorskip("mlx_lm")
    from keep.router import run_mlx_tools

    result = run_mlx_tools("find my resume")
    assert result is not None
    assert len(result) > 0


def test_execute_mlx_tool_call_returns_none_on_hallucinated_tool_name():
    from keep.router import _execute_mlx_tool_call

    # Real testing found the model invents a tool name outside this agent's
    # real four for prompts none of them fit (e.g. "what is 2+2" -> a call to
    # a nonexistent tool named "eval"). Testing the guard directly with a
    # hand-built dict, rather than waiting on the model to reproduce this
    # specific (non-deterministic -- see test_router.py's docstring) failure
    # on demand, makes this deterministic.
    result = _execute_mlx_tool_call({"name": "eval", "parameters": {"expression": "2+2"}})
    assert result is None


def test_execute_mlx_tool_call_returns_none_on_malformed_args():
    from keep.router import _execute_mlx_tool_call

    # A required arg missing entirely -- LangChain's ValidationError, caught
    # and turned into the same None contract as an unknown tool name.
    result = _execute_mlx_tool_call({"name": "search_files", "parameters": {"limit": 5}})
    assert result is None


def test_run_mlx_tools_coerces_string_typed_args():
    # Real testing found the model sometimes sends "limit": "10" (a string)
    # for search_files' int `limit` param -- this must not crash.
    from keep.router import _MLX_TOOLS

    result = _MLX_TOOLS["search_files"].invoke({"query": "resume", "limit": "10"})
    assert isinstance(result, str)


def test_run_mlx_tools_creates_and_cleans_up_reminder():
    pytest.importorskip("mlx_lm")
    from keep.router import run_mlx_tools

    mark = "KEEP-ROUTER-TEST-DELETE-ME"
    try:
        result = run_mlx_tools(f"create a reminder titled exactly '{mark}'")
        assert result is not None
        count = subprocess.run(
            ["osascript", "-e", f'''
            tell application "Reminders"
                tell default list
                    return count of (every reminder whose name contains "{mark}")
                end tell
            end tell
            '''],
            capture_output=True, text=True, timeout=90,
        ).stdout.strip()
        assert int(count) >= 1
    finally:
        subprocess.run(
            ["osascript", "-e", f'''
            tell application "Reminders"
                tell default list
                    delete (every reminder whose name contains "{mark}")
                end tell
            end tell
            '''],
            capture_output=True, text=True, timeout=90,
        )
