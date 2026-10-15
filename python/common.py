"""Shared helpers for the Python benchmarks: data loading, statistics, CSV output, cost models."""
import csv
import math
import os
import statistics

SIZES = [1_000, 10_000, 100_000, 1_000_000]
LANGUAGE = "Python"


def load_ints(path):
    with open(path, encoding="utf-8") as f:
        return [int(tok) for tok in f.read().split()]


def mean_std(values):
    """Mean and sample standard deviation (n-1)."""
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, std


def num(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return repr(float(value))


class CsvOut:
    """One CSV row per (algorithm, scenario, n). Flushed after every row so partial runs survive."""

    def __init__(self, path, scenario_col, reps):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._f = open(path, "w", newline="", encoding="utf-8")
        self._w = csv.writer(self._f)
        self.reps = reps
        self._w.writerow(
            ["language", "algorithm", scenario_col, "n"]
            + [f"rep{i + 1}" for i in range(reps)]
            + ["mean_s", "std_s", "measured", "status", "note"]
        )

    def row(self, algorithm, scenario, n, times, mean, std, measured, status, note=""):
        rep_cols = [num(t) for t in times] if times else [""] * self.reps
        self._w.writerow(
            [LANGUAGE, algorithm, scenario, n] + rep_cols
            + [num(mean), num(std) if measured else "", "true" if measured else "false", status, note]
        )
        self._f.flush()

    def close(self):
        self._f.close()


# --- Theoretical cost models, used only to ESTIMATE runs that are not executed -------------------

def predict(last_mean, last_n, cost, n):
    """Scale the last measured mean from last_n to n using the cost model."""
    if last_mean is None:
        return None
    return last_mean * cost(n) / cost(last_n)


def _n_log_n(n):
    return n * math.log2(n)


def _quadratic(n):
    return float(n) * n


def _linear(n):
    return float(n)


def _log_n(n):
    return math.log2(n)


def _sqrt_n(n):
    return math.sqrt(n)


def _log_log_n(n):
    return math.log2(math.log2(n))


def sort_model(algorithm, variant):
    if algorithm == "InsertionSort":
        return _linear if variant == "asc" else _quadratic
    if algorithm == "DualPivotQuickSort":
        return _n_log_n if variant == "random" else _quadratic
    if algorithm in ("MergeSort", "HeapSort"):
        return _n_log_n
    return _linear  # RadixSort (d = 8 digits) and BucketSort (uniform data)


def search_model(algorithm):
    return {
        "Linear": _linear,
        "Binary": _log_n,
        "Ternary": _log_n,
        "Jump": _sqrt_n,
        "Interpolation": _log_log_n,
        "Exponential": _log_n,
    }[algorithm]
