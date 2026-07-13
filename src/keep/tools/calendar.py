"""Calendar tool via AppleScript (Calendar.app) -- no extra dependencies needed."""

import subprocess

from keep.tools._applescript import escape
from keep.tools._dates import applescript_date_expr, normalize_date


def create_calendar_event(title: str, start_date: str, start_time: str = "09:00") -> str:
    """Create a new event on the user's default Calendar.

    Args:
        title: The event title.
        start_date: Date in MM/DD/YYYY format, e.g. "07/10/2026".
        start_time: Time in 24-hour HH:MM format, e.g. "14:30". Defaults to 09:00.
    """
    # An eval run found the model frequently computes its own start_date
    # wrong (see _dates.py) -- unlike a reminder's optional due_date, an
    # event can't just skip having a date, so an untrustworthy value is a
    # clear failure asking for a real date rather than a silent guess.
    normalized = normalize_date(start_date)
    if normalized is None:
        return (
            f"Could not create the event: '{start_date}' isn't a date I can trust "
            "(expected MM/DD/YYYY). Please give an exact date."
        )
    start_date = normalized
    title_e = escape(title)
    script = f'''
    {applescript_date_expr(start_date, start_time)}
    tell application "Calendar"
        tell calendar 1
            make new event with properties {{summary:"{title_e}", start date:theDate, end date:(theDate + 1 * hours)}}
        end tell
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            # A first-time user's very first calendar action pops macOS's
            # automation-consent dialog, which blocks osascript until it's
            # answered -- 10s is easily exceeded reading that dialog. An
            # uncaught TimeoutExpired here surfaced to the user as a raw
            # Python traceback via the agent's tool-error path (verified in
            # the pre-launch audit); matches reminders.py's own timeout for
            # the same reason.
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return (
            "Creating the event took too long -- if macOS just asked for "
            "permission to control Calendar, please allow it and try again."
        )
    if result.returncode != 0:
        return f"Failed to create event: {result.stderr.strip()}"
    return f"Created event '{title}' on {start_date} at {start_time}."
