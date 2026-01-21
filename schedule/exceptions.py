from collections.abc import Hashable
import datetime
import functools
import logging
import random
import re
import time
from typing import Set, List, Optional, Callable, Union

logger = logging.getLogger("schedule")


class ScheduleError(Exception):
    """Base schedule exception"""

    pass


class ScheduleValueError(ScheduleError):
    """Base schedule value error"""

    pass


class IntervalError(ScheduleValueError):
    """An improper interval was used"""

    pass


class CancelJob:
    """
    Can be returned from a job to unschedule itself.
    """

    pass
