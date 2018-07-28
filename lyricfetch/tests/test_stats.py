"""
Tests for the `Stats` and `Record` classes.
"""
import sys
import pytest

from lyrics import Record, Stats
from lyrics import avg
from lyrics import azlyrics
from lyrics import metrolyrics


def some_source():
    pass


def other_source():
    pass


def statistics():
    """
    Create a Stats object and fill it up with some results.
    """
    stats = Stats()
    stats.add_result(some_source, True, 2)
    stats.add_result(other_source, True, 1)
    stats.add_result(other_source, True, 1)
    stats.add_result(other_source, False, 1)
    return stats


def test_record_add_runtime():
    """
    Check that runtimes are correctly added to a record.
    """
    record = Record()
    record.add_runtime(10)
    record.add_runtime(20)
    assert record.runtimes == [10, 20]


def test_record_success_rate():
    """
    Check that a record returns the correct success rate.
    """
    record = Record()
    assert record.success_rate() == 0

    record.successes = 5
    record.fails = 5
    assert record.success_rate() == 50
    record.fails = 0
    assert record.success_rate() == 100
    record.fails = 5
    record.successes = 0
    assert record.success_rate() == 0


def test_avg():
    """
    Check that the `avg()` function returns the average of a sequence of
    numbers
    """
    assert avg([]) == 0
    assert avg([1, 2, 3]) == 2
    assert avg([42, 42, 42, 42, 42]) == 42
    assert avg((10, 50, 60)) == 40


def test_stats_add_result():
    """
    Test that `Stats.add_result` works.
    """
    stats = statistics()
    source_stats = stats.source_stats[some_source.__name__]
    assert source_stats.successes == 1
    assert source_stats.fails == 0
    assert source_stats.runtimes == [2]
    source_stats = stats.source_stats[other_source.__name__]
    assert source_stats.successes == 2
    assert source_stats.fails == 1
    assert source_stats.runtimes == [1, 1, 1]


def test_stats_avg_time():
    """
    Test that stats return the correct average.
    """
    stats = statistics()
    all_times = [t for r in stats.source_stats.values() for t in r.runtimes]
    assert stats.avg_time() == avg(all_times)
    average = avg(stats.source_stats['some_source'].runtimes)
    assert stats.avg_time(some_source) == average
    average = avg(stats.source_stats['other_source'].runtimes)
    assert stats.avg_time('other_source') == average


def test_stats_calculate():
    """
    Check the calculations of all the parameters in `Stats.calculate()`.
    """
    stats = Stats()
    stats.add_result(azlyrics, True, 1)
    stats.add_result(azlyrics, True, 1)
    stats.add_result(azlyrics, True, 1)
    stats.add_result(azlyrics, False, 1)
    stats.add_result(metrolyrics, False, 2)
    stats.add_result(metrolyrics, False, 2)
    stats.add_result(metrolyrics, False, 2)
    calc = stats.calculate()

    assert calc == {
        'best': ('azlyrics', 3, 75),
        'worst': ('metrolyrics', 0, 0),
        'fastest': ('azlyrics', 1),
        'slowest': ('metrolyrics', 2),
        'found': 3,
        'notfound': 4,
        'total_time': 10
    }
