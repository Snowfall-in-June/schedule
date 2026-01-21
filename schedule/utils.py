import datetime

from .exceptions import ScheduleValueError


def _move_to_next_weekday(moment: datetime.datetime, weekday: str):
    """
    Move the given timestamp to the nearest given weekday. May be this week
    or next week. If the timestamp is already at the given weekday, it is not
    moved.
    """
    weekday_index = _weekday_index(weekday)

    days_ahead = weekday_index - moment.weekday()
    if days_ahead < 0:
        # Target day already happened this week, move to next week
        days_ahead += 7
    return moment + datetime.timedelta(days=days_ahead)


def _weekday_index(day: str) -> int:
    weekdays = (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
    if day not in weekdays:
        raise ScheduleValueError(
            "Invalid start day (valid start days are {})".format(weekdays)
        )
    return weekdays.index(day)
