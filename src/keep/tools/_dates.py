"""Shared date normalization for tools that take a due_date/start_date arg.

An eval run (scripts/eval_agent.py) found the on-device model sends a
non-MM/DD/YYYY date on 89% of tool calls that included one -- not just
"today"/"tomorrow" as plain language, but often a specific YYYY-MM-DD date
the model computed itself, frequently one that's simply wrong (months or
years in the past relative to the real system date). The model appears to
reason about relative dates from an internal notion of "today" that doesn't
match the actual current date, and sometimes invents a due date even when
the request had no date reference at all.

Given that, trusting any date the model computed itself is unsafe. The
policy here: recognize a small set of relative phrases and compute them
ourselves from the real system clock; for anything else, if it isn't
already a plausible MM/DD/YYYY, drop it rather than pass along a date that
might be silently wrong. A reminder with no due date is a much smaller
problem than one with a confidently wrong one.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

_MM_DD_YYYY = re.compile(r"^\d{2}/\d{2}/\d{4}$")

_SIMPLE_OFFSETS = {
    "today": 0,
    "tomorrow": 1,
}

_IN_N_DAYS = re.compile(r"^in (\d+) days?$")


def normalize_date(raw: Optional[str]) -> Optional[str]:
    """Return a real MM/DD/YYYY string, or None if raw can't be trusted."""
    if not raw:
        return None

    key = raw.strip().lower()

    if _MM_DD_YYYY.match(raw.strip()):
        # The regex only checks shape (two digits/two digits/four digits) --
        # it accepts 13/45/2026, which AppleScript then silently rolls over
        # to a different real date instead of rejecting. strptime enforces
        # an actual calendar-valid month/day.
        try:
            datetime.strptime(raw.strip(), "%m/%d/%Y")
            return raw.strip()
        except ValueError:
            return None

    if key in _SIMPLE_OFFSETS:
        return _in_days(_SIMPLE_OFFSETS[key])

    if key == "next week":
        return _in_days(7)

    if key == "this weekend":
        return _next_weekday(5)  # Saturday

    match = _IN_N_DAYS.match(key)
    if match:
        return _in_days(int(match.group(1)))

    # Anything else (a model-hallucinated YYYY-MM-DD, prose like "December
    # 20th", ambiguous "15-10-24", etc.) is not trustworthy enough to act
    # on -- drop it rather than risk a confidently wrong date.
    return None


def applescript_date_expr(mm_dd_yyyy: str, hh_mm: Optional[str] = None) -> str:
    """AppleScript statements that build the given MM/DD/YYYY (+ optional
    HH:MM, 24h) date into a variable named `theDate`, numerically -- never
    via `date "<string>"`. That string form is parsed in AppleScript's own
    interpretation of the *user's* system date-format setting, so a
    normalize_date()-approved "07/12/2026" (July 12th) silently reads as
    "12 July 2026" on any Mac set to a day-first locale -- correct dates
    landing on the wrong day for a majority-non-US audience. Building from
    named components (year/month/day/hours/minutes) is locale-independent.

    Day is set to 1 before year/month to avoid an invalid intermediate date
    (e.g. today the 31st + a shorter target month), then set for real after."""
    month, day, year = (int(p) for p in mm_dd_yyyy.split("/"))
    hours, minutes = (int(p) for p in hh_mm.split(":")) if hh_mm else (0, 0)
    return f'''
        set theDate to current date
        set day of theDate to 1
        set year of theDate to {year}
        set month of theDate to {month}
        set day of theDate to {day}
        set hours of theDate to {hours}
        set minutes of theDate to {minutes}
        set seconds of theDate to 0
    '''


def _in_days(n: int) -> str:
    return (datetime.now() + timedelta(days=n)).strftime("%m/%d/%Y")


def _next_weekday(target_weekday: int) -> str:
    # Monday=0 ... Sunday=6
    today = datetime.now()
    days_ahead = (target_weekday - today.weekday()) % 7
    days_ahead = days_ahead or 7  # "this weekend" always means the upcoming one, not today
    return (today + timedelta(days=days_ahead)).strftime("%m/%d/%Y")
