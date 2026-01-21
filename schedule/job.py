from collections.abc import Hashable
import datetime
import functools
import logging
import random
import re
import time
from typing import Set, List, Optional, Callable, Union

from .exceptions import ScheduleError, ScheduleValueError, IntervalError, CancelJob
from .utils import _move_to_next_weekday, _weekday_index

logger = logging.getLogger("schedule")


class Job:
    """
    A periodic job as used by :class:`Scheduler`.

    :param interval: A quantity of a certain time unit
    :param scheduler: The :class:`Scheduler <Scheduler>` instance that
                      this job will register itself with once it has
                      been fully configured in :meth:`Job.do()`.

    Every job runs at a given fixed time interval that is defined by:

    * a :meth:`time unit <Job.second>`
    * a quantity of `time units` defined by `interval`

    A job is usually created and returned by :meth:`Scheduler.every`
    method, which also defines its `interval`.
    """

    def __init__(self, interval: int, scheduler: Optional['Scheduler'] = None):
        self.interval: int = interval  # pause interval * unit between runs
        self.latest: Optional[int] = None  # upper limit to the interval
        self.job_func: Optional[functools.partial] = None  # the job job_func to run

        # time units, e.g. 'minutes', 'hours', ...
        self.unit: Optional[str] = None

        # optional time at which this job runs
        self.at_time: Optional[datetime.time] = None

        # optional time zone of the self.at_time field. Only relevant when at_time is not None
        self.at_time_zone = None

        # datetime of the last run
        self.last_run: Optional[datetime.datetime] = None

        # datetime of the next run
        self.next_run: Optional[datetime.datetime] = None

        # Weekday to run the job at. Only relevant when unit is 'weeks'.
        # For example, when asking 'every week on tuesday' the start_day is 'tuesday'.
        self.start_day: Optional[str] = None

        # optional time of final run
        self.cancel_after: Optional[datetime.datetime] = None

        self.tags: Set[Hashable] = set()  # unique set of tags for the job
        self.scheduler: Optional['Scheduler'] = scheduler  # scheduler to register with
        self.paused: bool = False  # flag indicating if the job is paused

    def __lt__(self, other) -> bool:
        """
        PeriodicJobs are sortable based on the scheduled time they
        run next.
        """
        return self.next_run < other.next_run

    def __str__(self) -> str:
        if hasattr(self.job_func, "__name__"):
            job_func_name = self.job_func.__name__  # type: ignore
        else:
            job_func_name = repr(self.job_func)

        return ("Job(interval={}, unit={}, do={}, args={}, kwargs={})").format(
            self.interval,
            self.unit,
            job_func_name,
            "()" if self.job_func is None else self.job_func.args,
            "{}" if self.job_func is None else self.job_func.keywords,
        )

    def __repr__(self):
        def format_time(t):
            return t.strftime("%Y-%m-%d %H:%M:%S") if t else "[never]"

        def is_repr(j):
            return not isinstance(j, Job)

        timestats = "(last run: %s, next run: %s)" % (
            format_time(self.last_run),
            format_time(self.next_run),
        )

        if hasattr(self.job_func, "__name__"):
            job_func_name = self.job_func.__name__
        else:
            job_func_name = repr(self.job_func)

        if self.job_func is not None:
            args = [repr(x) if is_repr(x) else str(x) for x in self.job_func.args]
            kwargs = ["%s=%s" % (k, repr(v)) for k, v in self.job_func.keywords.items()]
            call_repr = job_func_name + "(" + ", ".join(args + kwargs) + ")"
        else:
            call_repr = "[None]"

        if self.at_time is not None:
            return "Every %s %s at %s do %s %s" % (
                self.interval,
                self.unit[:-1] if self.interval == 1 else self.unit,
                self.at_time,
                call_repr,
                timestats,
            )
        else:
            fmt = (
                "Every %(interval)s "
                + ("to %(latest)s " if self.latest is not None else "")
                + "%(unit)s do %(call_repr)s %(timestats)s"
            )

            return fmt % dict(
                interval=self.interval,
                latest=self.latest,
                unit=(self.unit[:-1] if self.interval == 1 else self.unit),
                call_repr=call_repr,
                timestats=timestats,
            )

    @property
    def millisecond(self):
        if self.interval != 1:
            raise IntervalError("Use milliseconds instead of millisecond")
        return self.milliseconds

    @property
    def milliseconds(self):
        self.unit = "milliseconds"
        return self

    @property
    def second(self):
        if self.interval != 1:
            raise IntervalError("Use seconds instead of second")
        return self.seconds

    @property
    def seconds(self):
        self.unit = "seconds"
        return self

    @property
    def minute(self):
        if self.interval != 1:
            raise IntervalError("Use minutes instead of minute")
        return self.minutes

    @property
    def minutes(self):
        self.unit = "minutes"
        return self

    @property
    def hour(self):
        if self.interval != 1:
            raise IntervalError("Use hours instead of hour")
        return self.hours

    @property
    def hours(self):
        self.unit = "hours"
        return self

    @property
    def day(self):
        if self.interval != 1:
            raise IntervalError("Use days instead of day")
        return self.days

    @property
    def days(self):
        self.unit = "days"
        return self

    @property
    def week(self):
        if self.interval != 1:
            raise IntervalError("Use weeks instead of week")
        return self.weeks

    @property
    def weeks(self):
        self.unit = "weeks"
        return self

    @property
    def monday(self):
        if self.interval != 1:
            raise IntervalError(
                "Scheduling .monday() jobs is only allowed for weekly jobs. "
                "Using .monday() on a job scheduled to run every 2 or more weeks "
                "is not supported."
            )
        self.start_day = "monday"
        return self.weeks

    @property
    def tuesday(self):
        if self.interval != 1:
            raise IntervalError(
                "Scheduling .tuesday() jobs is only allowed for weekly jobs. "
                "Using .tuesday() on a job scheduled to run every 2 or more weeks "
                "is not supported."
            )
        self.start_day = "tuesday"
        return self.weeks

    @property
    def wednesday(self):
        if self.interval != 1:
            raise IntervalError(
                "Scheduling .wednesday() jobs is only allowed for weekly jobs. "
                "Using .wednesday() on a job scheduled to run every 2 or more weeks "
                "is not supported."
            )
        self.start_day = "wednesday"
        return self.weeks

    @property
    def thursday(self):
        if self.interval != 1:
            raise IntervalError(
                "Scheduling .thursday() jobs is only allowed for weekly jobs. "
                "Using .thursday() on a job scheduled to run every 2 or more weeks "
                "is not supported."
            )
        self.start_day = "thursday"
        return self.weeks

    @property
    def friday(self):
        if self.interval != 1:
            raise IntervalError(
                "Scheduling .friday() jobs is only allowed for weekly jobs. "
                "Using .friday() on a job scheduled to run every 2 or more weeks "
                "is not supported."
            )
        self.start_day = "friday"
        return self.weeks

    @property
    def saturday(self):
        if self.interval != 1:
            raise IntervalError(
                "Scheduling .saturday() jobs is only allowed for weekly jobs. "
                "Using .saturday() on a job scheduled to run every 2 or more weeks "
                "is not supported."
            )
        self.start_day = "saturday"
        return self.weeks

    @property
    def sunday(self):
        if self.interval != 1:
            raise IntervalError(
                "Scheduling .sunday() jobs is only allowed for weekly jobs. "
                "Using .sunday() on a job scheduled to run every 2 or more weeks "
                "is not supported."
            )
        self.start_day = "sunday"
        return self.weeks

    def tag(self, *tags: Hashable):
        """
        Tags the job with one or more unique identifiers.

        Tags must be hashable. Duplicate tags are discarded.

        :param tags: A unique list of ``Hashable`` tags.
        :return: The invoked job instance
        """
        if not all(isinstance(tag, Hashable) for tag in tags):
            raise TypeError("Tags must be hashable")
        self.tags.update(tags)
        return self

    def at(self, time_str: str, tz: Optional[str] = None):
        """
        Specify a particular time that the job should be run at.

        :param time_str: A string in one of the following formats:

            - For daily jobs -> `HH:MM:SS` or `HH:MM`
            - For hourly jobs -> `MM:SS` or `:MM`
            - For minute jobs -> `:SS`

            The format must make sense given how often the job is
            repeating; for example, a job that repeats every minute
            should not be given a string in the form `HH:MM:SS`. The
            difference between `:MM` and `:SS` is inferred from the
            selected time-unit (e.g. `every().hour.at(':30')` vs.
            `every().minute.at(':30')`).

        :param tz: The timezone that this timestamp refers to. Can be
            a string that can be parsed by pytz.timezone(), or a pytz.BaseTzInfo object

        :return: The invoked job instance
        """
        if self.unit not in ("days", "hours", "minutes") and not self.start_day:
            raise ScheduleValueError(
                "Invalid unit (valid units are `days`, `hours`, and `minutes`)"
            )

        if tz is not None:
            import pytz

            if isinstance(tz, str):
                self.at_time_zone = pytz.timezone(tz)  # type: ignore
            elif isinstance(tz, pytz.BaseTzInfo):
                self.at_time_zone = tz
            else:
                raise ScheduleValueError(
                    "Timezone must be string or pytz.timezone object"
                )

        if not isinstance(time_str, str):
            raise TypeError("at() should be passed a string")
        if self.unit == "days" or self.start_day:
            if not re.match(r"^[0-2]\d:[0-5]\d(:[0-5]\d)?$", time_str):
                raise ScheduleValueError(
                    "Invalid time format for a daily job (valid format is HH:MM(:SS)?)")
        if self.unit == "hours":
            if not re.match(r"^([0-5]\d)?:[0-5]\d$", time_str):
                raise ScheduleValueError(
                    "Invalid time format for an hourly job (valid format is (MM)?:SS)"
                )

        if self.unit == "minutes":
            if not re.match(r"^:[0-5]\d$", time_str):
                raise ScheduleValueError(
                    "Invalid time format for a minutely job (valid format is :SS)"
                )
        time_values = time_str.split(":")
        hour: Union[str, int]
        minute: Union[str, int]
        second: Union[str, int]
        if len(time_values) == 3:
            hour, minute, second = time_values
        elif len(time_values) == 2 and self.unit == "minutes":
            hour = 0
            minute = 0
            _, second = time_values
        elif len(time_values) == 2 and self.unit == "hours" and len(time_values[0]):
            hour = 0
            minute, second = time_values
        else:
            hour, minute = time_values
            second = 0
        if self.unit == "days" or self.start_day:
            hour = int(hour)
            if not (0 <= hour <= 23):
                raise ScheduleValueError(
                    "Invalid number of hours ({} is not between 0 and 23)"
                )
        elif self.unit == "hours":
            hour = 0
        elif self.unit == "minutes":
            hour = 0
            minute = 0
        hour = int(hour)
        minute = int(minute)
        second = int(second)
        self.at_time = datetime.time(hour, minute, second)
        return self

    def to(self, latest: int):
        """
        Schedule the job to run at an irregular (randomized) interval.

        The job's interval will randomly vary from the value given
        to  `every` to `latest`. The range defined is inclusive on
        both ends. For example, `every(A).to(B).seconds` executes
        the job function every N seconds such that A <= N <= B.

        :param latest: Maximum interval between randomized job runs
        :return: The invoked job instance
        """
        self.latest = latest
        return self

    def until(
        self,
        until_time: Union[datetime.datetime, datetime.timedelta, datetime.time, str],
    ):
        """
        Schedule job to run until the specified moment.

        The job is canceled whenever the next run is calculated and it turns out the
        next run is after the until_time. The job is also canceled right before it runs,
        if the current time is after until_time. This latter case can happen when the
        the job was scheduled to run before until_time, but runs after until_time.

        If until_time is a moment in the past, ScheduleValueError is thrown.

        :param until_time: A moment in the future representing the latest time a job can
           be run. If only a time is supplied, the date is set to today.
           The following formats are accepted:

           - datetime.datetime
           - datetime.timedelta
           - datetime.time
           - String in one of the following formats: "%Y-%m-%d %H:%M:%S",
             "%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M:%S", "%H:%M"
             as defined by strptime() behaviour. If an invalid string format is passed,
             ScheduleValueError is thrown.

        :return: The invoked job instance
        """

        if isinstance(until_time, datetime.datetime):
            self.cancel_after = until_time
        elif isinstance(until_time, datetime.timedelta):
            self.cancel_after = datetime.datetime.now() + until_time
        elif isinstance(until_time, datetime.time):
            self.cancel_after = datetime.datetime.combine(
                datetime.datetime.now(), until_time
            )
        elif isinstance(until_time, str):
            cancel_after = self._decode_datetimestr(
                until_time,
                [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d",
                    "%H:%M:%S",
                    "%H:%M",
                ],
            )
            if cancel_after is None:
                raise ScheduleValueError("Invalid string format for until()")
            if "-" not in until_time:
                # the until_time is a time-only format. Set the date to today
                now = datetime.datetime.now()
                cancel_after = cancel_after.replace(
                    year=now.year, month=now.month, day=now.day
                )
            self.cancel_after = cancel_after
        else:
            raise TypeError(
                "until() takes a string, datetime.datetime, datetime.timedelta, "
                "datetime.time parameter"
            )
        if self.cancel_after < datetime.datetime.now():
            raise ScheduleValueError(
                "Cannot schedule a job to run until a time in the past"
            )
        return self

    def do(self, job_func: Callable, *args, **kwargs):
        """
        Specifies the job_func that should be called every time the
        job runs.

        Any additional arguments are passed on to job_func when
        the job runs.

        :param job_func: The function to be scheduled
        :return: The invoked job instance
        """
        self.job_func = functools.partial(job_func, *args, **kwargs)
        functools.update_wrapper(self.job_func, job_func)
        self._schedule_next_run()
        if self.scheduler is None:
            raise ScheduleError(
                "Unable to a add job to schedule. "
                "Job is not associated with an scheduler"
            )
        with self.scheduler._lock:
            self.scheduler.jobs.append(self)
        return self

    @property
    def should_run(self) -> bool:
        """
        :return: ``True`` if the job should be run now.
        """
        assert self.next_run is not None, "must run _schedule_next_run before"
        return not self.paused and datetime.datetime.now() >= self.next_run

    def run(self):
        """
        Run the job and immediately reschedule it.
        If the job's deadline is reached (configured using .until()), the job is not
        run and CancelJob is returned immediately. If the next scheduled run exceeds
        the job's deadline, CancelJob is returned after the execution. In this latter
        case CancelJob takes priority over any other returned value.

        :return: The return value returned by the `job_func`, or CancelJob if the job's
                 deadline is reached.

        """
        if self._is_overdue(datetime.datetime.now()):
            logger.debug("Cancelling job %s", self)
            return CancelJob

        logger.debug("Running job %s", self)
        ret = self.job_func()
        self.last_run = datetime.datetime.now()
        self._schedule_next_run()

        if self._is_overdue(self.next_run):
            logger.debug("Cancelling job %s", self)
            return CancelJob
        return ret

    def _schedule_next_run(self) -> None:
        """
        Compute the instant when this job should run next.
        """
        if self.unit not in ("milliseconds", "seconds", "minutes", "hours", "days", "weeks"):
            raise ScheduleValueError(
                "Invalid unit (valid units are `milliseconds`, `seconds`, `minutes`, `hours`, "
                "`days`, and `weeks`)"
            )
        if self.latest is not None:
            if not (self.latest >= self.interval):
                raise ScheduleError("`latest` is greater than `interval`")
            interval = random.randint(self.interval, self.latest)
        else:
            interval = self.interval

        # Do all computation in the context of the requested timezone
        now = datetime.datetime.now(self.at_time_zone)

        next_run = now

        if self.start_day is not None:
            if self.unit != "weeks":
                raise ScheduleValueError("`unit` should be 'weeks'")
            next_run = _move_to_next_weekday(next_run, self.start_day)

        if self.at_time is not None:
            next_run = self._move_to_at_time(next_run)

        period = datetime.timedelta(**{self.unit: interval})
        if interval != 1:
            next_run += period

        while next_run <= now:
            next_run += period

        next_run = self._correct_utc_offset(
            next_run, fixate_time=(self.at_time is not None)
        )

        # To keep the api consistent with older versions, we have to set the 'next_run' to a naive timestamp in the local timezone.
        # Because we want to stay backwards compatible with older versions.
        if self.at_time_zone is not None:
            # Convert back to the local timezone
            next_run = next_run.astimezone()

            next_run = next_run.replace(tzinfo=None)

        self.next_run = next_run

    def _move_to_at_time(self, moment: datetime.datetime) -> datetime.datetime:
        """
        Takes a datetime and moves the time-component to the job's at_time.
        """
        if self.at_time is None:
            return moment

        kwargs = {"second": self.at_time.second, "microsecond": 0}

        if self.unit == "days" or self.start_day is not None:
            kwargs["hour"] = self.at_time.hour

        if self.unit in ["days", "hours"] or self.start_day is not None:
            kwargs["minute"] = self.at_time.minute

        moment = moment.replace(**kwargs)  # type: ignore

        # When we set the time elements, we might end up in a different UTC-offset than the current offset.
        # This happens when we cross into or out of daylight saving time.
        moment = self._correct_utc_offset(moment, fixate_time=True)

        return moment

    def _correct_utc_offset(
        self, moment: datetime.datetime, fixate_time: bool
    ) -> datetime.datetime:
        """
        Given a datetime, corrects any mistakes in the utc offset.
        This is similar to pytz' normalize, but adds the ability to attempt
        keeping the time-component at the same hour/minute/second.
        """
        if self.at_time_zone is None:
            return moment
        # Normalize corrects the utc-offset to match the timezone
        # For example: When a date&time&offset does not exist within a timezone,
        # the normalization will change the utc-offset to where it is valid.
        # It does this while keeping the moment in time the same, by moving the
        # time component opposite of the utc-change.
        offset_before_normalize = moment.utcoffset()
        moment = self.at_time_zone.normalize(moment)
        offset_after_normalize = moment.utcoffset()

        if offset_before_normalize == offset_after_normalize:
            # There was no change in the utc-offset, datetime didn't change.
            return moment

        # The utc-offset and time-component has changed

        if not fixate_time:
            # No need to fixate the time.
            return moment

        offset_diff = offset_after_normalize - offset_before_normalize

        # Adjust the time to reset the date-time to have the same HH:mm components
        moment -= offset_diff

        # Check if moving the timestamp back by the utc-offset-difference made it end up
        # in a moment that does not exist within the current timezone/utc-offset
        re_normalized_offset = self.at_time_zone.normalize(moment).utcoffset()
        if re_normalized_offset != offset_after_normalize:
            # We ended up in a DST Gap. The requested 'at' time does not exist
            # within the current timezone/utc-offset. As a best effort, we will
            # schedule the job 1 offset later than possible.
            # For example, if 02:23 does not exist (because DST moves from 02:00
            # to 03:00), this will schedule the job at 03:23.
            moment += offset_diff
        return moment

    def _is_overdue(self, when: datetime.datetime):
        return self.cancel_after is not None and when > self.cancel_after

    def _decode_datetimestr(
        self, datetime_str: str, formats: List[str]
    ) -> Optional[datetime.datetime]:
        for f in formats:
            try:
                return datetime.datetime.strptime(datetime_str, f)
            except ValueError:
                pass
        return None

    def pause(self) -> 'Job':
        """
        Pause the job, preventing it from running until resumed.
        
        :return: The invoked job instance
        """
        self.paused = True
        logger.debug("Pausing job %s", self)
        return self

    def resume(self) -> 'Job':
        """
        Resume a paused job, allowing it to run again.
        
        :return: The invoked job instance
        """
        self.paused = False
        logger.debug("Resuming job %s", self)
        return self

    def is_paused(self) -> bool:
        """
        :return: ``True`` if the job is currently paused.
        """
        return self.paused
