"""Temporal metadata signal: scores how stale a document's ms.date is."""
from datetime import date, datetime

from extract_date import FETCH_FAILED, UNKNOWN

FRESH_MONTHS = 12
NOT_APPLICABLE = "not_applicable"
# ms.date in the corpus is MM/DD/YYYY; ISO dates are accepted too.
_DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d")


def parse_date(value):
    """Parse an ms.date string (MM/DD/YYYY or YYYY-MM-DD) into a date."""
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value!r}")


def months_between(start, end):
    """Whole calendar months elapsed from start to end (negative if start is later)."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def check_temporal_metadata(ms_date, today=None, ambiguous_date_format=False):
    """Return {'date', 'months_old', 'score', 'low_confidence'}.

    score is 0 when the date is within FRESH_MONTHS, otherwise 1 point per full
    month beyond that. `today` defaults to the actual current date.

    Special inputs from extract_date.py:
    - "date_unknown" / "fetch_failed": no date to judge, so score is
      "not_applicable" (date and months_old are None). Callers must exclude
      these from any summing/averaging; they are neither fresh nor stale.
    - ambiguous_date_format=True: scored normally, but low_confidence is True
      because the day/month order of the source date was a guess.
    """
    if ms_date in (UNKNOWN, FETCH_FAILED):
        return {"date": None, "months_old": None, "score": NOT_APPLICABLE,
                "low_confidence": False, "reason": ms_date}
    today = today or date.today()
    d = parse_date(ms_date)
    months_old = months_between(d, today)
    score = max(0, months_old - FRESH_MONTHS)
    return {"date": d, "months_old": months_old, "score": score,
            "low_confidence": bool(ambiguous_date_format)}


if __name__ == "__main__":
    today = date.today()
    print(f"Today: {today}\n")
    cases = [
        ("normal recent date", "05/01/2026", False),
        ("date_unknown", "date_unknown", False),
        ("fetch_failed", "fetch_failed", False),
        ("ambiguous date format", "2019-03-04", True),
    ]
    for label, raw, ambiguous in cases:
        r = check_temporal_metadata(raw, today, ambiguous)
        print(f"{label}: input={raw!r} ambiguous={ambiguous}")
        print(f"   months_old={r['months_old']} score={r['score']} "
              f"low_confidence={r['low_confidence']}")
