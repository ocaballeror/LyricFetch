"""
A collection of classes and methods to accumulate, calculate and show stats
about an execution.
"""
from collections import defaultdict

from . import sources


def avg(values):
    """
    Returns the average of a sequence of numbers.
    """
    if not values:
        return 0
    else:
        return sum(values) / len(values)


class Record:
    """
    Defines an entry in the stats 'database'. Packs a set of information about
    an execution of the scrapping functions. This class is auxiliary to Stats.
    """
    def __init__(self):
        self.successes = 0
        self.fails = 0
        self.runtimes = []

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"""Successes: {self.successes}
Fails: {self.fails}
Success rate: {self.success_rate():.2f}%
Average runtime: {avg(self.runtimes):.2f}s"""

    def add_runtime(self, runtime):
        """
        Add a new runtime to the runtimes dictionary.
        """
        if runtime != 0:
            self.runtimes.append(runtime)

    def success_rate(self):
        """
        Returns a float with the rate of success from all the logged results.
        """
        if self.successes + self.fails == 0:
            success_rate = 0
        else:
            total_attempts = self.successes + self.fails
            success_rate = (self.successes * 100 / total_attempts)

        return success_rate


class Stats:
    """
    Stores a series of statistics about the execution of the program.
    """
    def __init__(self):
        # Maps every lyrics scraping function to a Record object
        self.source_stats = defaultdict(Record)

    def add_result(self, source, found, runtime):
        """
        Adds a new record to the statistics 'database'. This function is
        intended to be called after a website has been scraped. The arguments
        indicate the function that was called, the time taken to scrap the
        website and a boolean indicating if the lyrics were found or not.
        """
        self.source_stats[source.__name__].add_runtime(runtime)
        if found:
            self.source_stats[source.__name__].successes += 1
        else:
            self.source_stats[source.__name__].fails += 1

    def avg_time(self, source=None):
        """
        Returns the average time taken to scrape lyrics. If a string or a
        function is passed as source, return the average time taken to scrape
        lyrics from that source, otherwise return the total average.
        """
        if source is None:
            runtimes = []
            for rec in self.source_stats.values():
                runtimes.extend([r for r in rec.runtimes if r != 0])
            return avg(runtimes)
        else:
            if callable(source):
                return avg(self.source_stats[source.__name__].runtimes)
            else:
                return avg(self.source_stats[source].runtimes)

    def calculate(self):
        """
        Calculate the overall counts of best, worst, fastest, slowest, total
        found, total not found and total runtime

        Results are returned in a dictionary with the above parameters as keys.
        """
        best, worst, fastest, slowest = (), (), (), ()
        found = notfound = total_time = 0
        for source, rec in self.source_stats.items():
            if not best or rec.successes > best[1]:
                best = (source, rec.successes, rec.success_rate())
            if not worst or rec.successes < worst[1]:
                worst = (source, rec.successes, rec.success_rate())

            avg_time = self.avg_time(source)
            if not fastest or (avg_time != 0 and avg_time < fastest[1]):
                fastest = (source, avg_time)
            if not slowest or (avg_time != 0 and avg_time > slowest[1]):
                slowest = (source, avg_time)

            found += rec.successes
            notfound += rec.fails
            total_time += sum(rec.runtimes)

        return {
            'best': best,
            'worst': worst,
            'fastest': fastest,
            'slowest': slowest,
            'found': found,
            'notfound': notfound,
            'total_time': total_time
        }

    def print_stats(self):
        """
        Print a series of relevant stats about a full execution. This function
        is meant to be called at the end of the program.
        """
        stats = self.calculate()
        total_time = '%d:%02d:%02d' % (stats['total_time'] / 3600,
                                       (stats['total_time'] / 3600) / 60,
                                       (stats['total_time'] % 3600) % 60)
        output = """\
Total runtime: {total_time}
    Lyrics found: {found}
    Lyrics not found:{notfound}
    Most useful source:\
{best} ({best_count} lyrics found) ({best_rate:.2f}% success rate)
    Least useful source:\
{worst} ({worst_count} lyrics found) ({worst_rate:.2f}% success rate)
    Fastest website to scrape: {fastest} (Avg: {fastest_time:.2f}s per search)
    Slowest website to scrape: {slowest} (Avg: {slowest_time:.2f}s per search)
    Average time per website: {avg_time:.2f}s

xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxx    PER WEBSITE STATS:      xxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""
        output = output.format(total_time=total_time,
                               found=stats['found'],
                               notfound=stats['notfound'],
                               best=stats['best'][0].capitalize(),
                               best_count=stats['best'][1],
                               best_rate=stats['best'][2],
                               worst=stats['worst'][0].capitalize(),
                               worst_count=stats['worst'][1],
                               worst_rate=stats['worst'][2],
                               fastest=stats['fastest'][0].capitalize(),
                               fastest_time=stats['fastest'][1],
                               slowest=stats['slowest'][0].capitalize(),
                               slowest_time=stats['slowest'][1],
                               avg_time=self.avg_time())
        for source in sources:
            stat = str(self.source_stats[source.__name__])
            output += f'\n{source.__name__.upper()}\n{stat}\n'

        print(output)
