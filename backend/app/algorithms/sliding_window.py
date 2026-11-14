"""Fixed-size sliding window over a chronological series.

Used for 7-day and 30-day consumption averages. Each new day adds one
observation and, once the window is full, drops the day that just left
the window. The running sum makes every step O(1).

rolling_averages: O(n) time, O(n) output, O(1) extra working memory.
window_average:   O(n) time, O(1) extra memory beyond the output of the scan.

Missing calendar days must already be filled with zero by the caller.
Averaging only the days that had a sale would overstate demand.
"""

from decimal import Decimal


def _decimal(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def rolling_averages(values, window):
    """Return the average of each suffix window as the series is scanned.

    The first averages use fewer than `window` points. From index
    `window - 1` onward, each average covers exactly `window` observations.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    running = Decimal("0")
    averages = []
    series = list(values)
    for index, value in enumerate(series):
        running += _decimal(value)
        if index >= window:
            running -= _decimal(series[index - window])
        length = min(index + 1, window)
        averages.append(running / Decimal(length))
    return averages


def window_average(values, window):
    """Average of the latest window, or None when the series is empty."""
    if not values:
        return None
    return rolling_averages(values, window)[-1]


class SlidingWindow:
    """Small wrapper so call sites can name the window they are using."""

    def __init__(self, values, window):
        if window <= 0:
            raise ValueError("window must be positive")
        self.values = list(values)
        self.window = int(window)

    def averages(self):
        return rolling_averages(self.values, self.window)

    def latest(self):
        if not self.values:
            return None
        return self.averages()[-1]

    def __len__(self):
        return len(self.values)
