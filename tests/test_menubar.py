"""Real test for the menu bar's single-in-flight busy guard -- doesn't
require a running NSApplication event loop, just the app object itself."""

from keep.menubar import KeepApp


def test_start_busy_guards_against_concurrent_actions():
    app = KeepApp()
    assert app._try_start_busy() is True
    assert app._busy is True

    # A second start while busy is refused, not queued.
    assert app._try_start_busy() is False

    # Once cleared (as every terminal UI branch does), it's available again.
    app._busy = False
    assert app._try_start_busy() is True
