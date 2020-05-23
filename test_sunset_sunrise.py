"""Test the addition of sunset/sunrise time scheduling based on the location.

.. module:: test.sunset.sunrise
   :synopsis: test the addition of sunset/sunrise time scheduling based on the location

.. moduleauthor:: Bryant Finney <bryant@outdoorlinkinc.com>
   :github: https://github.com/bryant-finney/
"""
# stdlib
import datetime as dt
import functools
import logging

# third party
import pytest

# local
import schedule
from test_schedule import mock_datetime

OFFSETS = [0, 1, 2, 3, 5, 7, 10, 15, 20, 30, 45, 60]
logger = logging.getLogger(__name__)


def mock_func(*args, **kwargs):
    logger.info("test_func(*%s, **%s)", args, kwargs)


def test_api():
    assert hasattr(schedule.Job, "after")
    assert hasattr(schedule.Job, "offset")


@pytest.mark.parametrize("offset", OFFSETS + [-o for o in OFFSETS[1:]])
@pytest.mark.parametrize("units", schedule.TIME_UNITS)
def test_offset_after_units(offset, units):
    """Verify the next run time is calculated correctly after setting the offset."""
    t = dt.datetime(2020, 5, 22, 10, 22)
    with mock_datetime(t.year, t.month, t.day, t.hour, t.minute, t.second):
        job = schedule.every().week.after(offset, units).do(mock_func, [offset, units])
        assert job.offset == dt.timedelta(**{units: offset})
        assert job.offset_unit == units
        assert job.next_run == t + job.period + job.offset


@pytest.mark.parametrize("units", schedule.TIME_UNITS)
def test_singular_units(units):
    """Verify that 's' is appended to singular unit values."""
    job = schedule.every().week.after(1, units[:-1]).do(mock_func, [1, units[:-1]])
    assert job.offset_unit == units


def test_always_after():
    """Verify that that the offset is always applied when `always` == True."""
    offset = 2
    units = "hours"
    t = dt.datetime(2020, 5, 22, 10, 22)
    with mock_datetime(t.year, t.month, t.day, t.hour, t.minute, t.second):
        job = (
            schedule.every(3)
            .days.after(offset, units)
            .at("10:00")
            .do(mock_func, [offset, units])
        )

    assert job.offset < job.period

    job_offset = job.offset
    t_ = t + job_offset
    with mock_datetime(t_.year, t_.month, t_.day, t_.hour, t_.minute, t_.second + 1):
        schedule.run_pending()
        assert job.last_run is None, "job should not have run yet; must wait for period"

    last_run = None
    for period_num in range(1, 4):
        t_ = t + job_offset + period_num * job.period
        with mock_datetime(
            t_.year, t_.month, t_.day, t_.hour, t_.minute, t_.second + 1
        ):
            schedule.run_pending()
            assert job.last_run is not None
            if last_run is None:
                last_run = job.last_run
            else:
                assert job.last_run != last_run

    assert job.offset == job_offset


def test_not_always_after():
    """Verify that that the offset is always applied when `always` == True."""
    offset = 2
    units = "hours"
    t = dt.datetime(2020, 5, 22, 10, 22)
    with mock_datetime(t.year, t.month, t.day, t.hour, t.minute, t.second):
        job = (
            schedule.every(3)
            .days.after(offset, units, always=False)
            .at("10:20")
            .do(mock_func, [offset, units])
        )
        assert job.offset_once

    job_offset = job.offset
    t_ = t + job_offset
    with mock_datetime(t_.year, t_.month, t_.day, t_.hour, t_.minute, t_.second + 1):
        schedule.run_pending()
        assert job.last_run is None, "job should not have run yet; must wait for period"

    last_run = None
    for period_num in range(1, 4):
        t_ = t + int(period_num == 1) * job_offset + period_num * job.period
        with mock_datetime(
            t_.year, t_.month, t_.day, t_.hour, t_.minute, t_.second + 1
        ):
            schedule.run_pending()
            assert job.last_run is not None
            if last_run is None:
                last_run = job.last_run
            else:
                assert job.last_run != last_run

    # the value of the offset shouldn't change, even though it was only followed once
    assert job.offset == job_offset


def test_invalid_units():
    with pytest.raises(schedule.ScheduleValueError):
        schedule.every(30).seconds.after(5, "fake-unit").do(mock_func, [5, "fake-unit"])


def test_partial_func():
    test_func = functools.partial(mock_func, ["test", "partial"])
    job = schedule.every(60).seconds.do(test_func, kwargs={"sample": "kwargs"})
    assert not hasattr(job.job_func, "__name__")


def test_multiple_jobs_with_offsets():
    """Test five jobs run every five minutes; each a one-minute offset from the last."""
    scheduler = schedule.Scheduler()

    t_0 = dt.datetime(2020, 5, 22, 10, 22)
    with mock_datetime(t_0.year, t_0.month, t_0.day, t_0.hour, t_0.minute, t_0.second):
        jobs = [scheduler.every(5).minutes.do(mock_func, kwargs={"i_schedule": 0})]
        for i_schedule in range(1, 5):
            jobs.append(
                scheduler.every(5)
                .minutes.do(mock_func, kwargs={"schedule_num": i_schedule})
                .after(i_schedule, "minute")
            )
        assert scheduler.idle_seconds >= 5 * 60
        assert scheduler.next_run == t_0 + dt.timedelta(minutes=5)

    for n_minutes_offset in range(0, 20):
        t = t_0 + dt.timedelta(minutes=5) + dt.timedelta(minutes=n_minutes_offset)
        with mock_datetime(t.year, t.month, t.day, t.hour, t.minute, t.second):
            assert scheduler.idle_seconds <= 0
            assert scheduler.next_run == t
            scheduler.run_pending()
            assert scheduler.jobs[n_minutes_offset % 5].last_run == t
            assert scheduler.next_run == t + dt.timedelta(minutes=1)
