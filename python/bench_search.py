#!/usr/bin/env python3
"""Point 2 benchmark (Python).

Usage: python python/bench_search.py [--data data] [--out results/search_python.csv]
                                     [--max-n 1000000] [--reps 5] [--limit-seconds 300]

Scenarios: keyset (the 1,000 keys of keys_<n>.txt) at every n, and pos_start / pos_center / pos_end
(the same key searched 1,000 times) at the largest n only. Reported time = seconds per search.
"""
import argparse
import os
import time
from bisect import bisect_left

import searching
from common import SIZES, CsvOut, load_ints, mean_std, predict, search_model

POSITION_REPEATS = 1_000
ALGOS = {
    "Linear": searching.linear_search,
    "Binary": searching.binary_search,
    "Ternary": searching.ternary_search,
    "Jump": searching.jump_search,
    "Interpolation": searching.interpolation_search,
    "Exponential": searching.exponential_search,
}


def time_keys(fn, arr, keys):
    """Seconds per search for one pass over all keys, plus the results (for verification)."""
    res = [0] * len(keys)
    t0 = time.perf_counter_ns()
    for i in range(len(keys)):
        res[i] = fn(arr, keys[i])
    t1 = time.perf_counter_ns()
    return (t1 - t0) / 1e9 / len(keys), res


def verify(arr, keys, res):
    for key, r in zip(keys, res):
        j = bisect_left(arr, key)
        present = j < len(arr) and arr[j] == key
        if present:
            if r < 0 or arr[r] != key:
                return False
        elif r != -1:
            return False
    return True


def run_scenario(out, name, scenario, fn, arr, keys, n, reps):
    times, ok = [], True
    for _ in range(reps):
        t, res = time_keys(fn, arr, keys)
        times.append(t)
        ok = ok and verify(arr, keys, res)  # verification, not timed
    mean, std = mean_std(times)
    out.row(name, scenario, n, times, mean, std, True, "OK" if ok else "VERIFICATION_FAILED")
    print(f"{name:<14} {scenario:<11} n={n:<8} mean={mean:.3e} s/search", flush=True)
    return mean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="results/search_python.csv")
    ap.add_argument("--max-n", type=int, default=1_000_000)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--limit-seconds", type=float, default=300.0)
    args = ap.parse_args()

    sizes = [n for n in SIZES if n <= args.max_n]
    position_n = sizes[-1]
    arrays = {n: load_ints(os.path.join(args.data, f"asc_{n}.txt")) for n in sizes}
    keys = {n: load_ints(os.path.join(args.data, f"keys_{n}.txt")) for n in sizes}

    out = CsvOut(args.out, "scenario", args.reps)
    try:
        for name, fn in ALGOS.items():
            cost = search_model(name)
            last_mean, last_n = None, 0
            for n in sizes:
                est = predict(last_mean, last_n, cost, n)
                if est is not None and est * len(keys[n]) > args.limit_seconds:
                    out.row(name, "keyset", n, None, est, None, False, "ESTIMATED",
                            f"predicted > limit; scaled from n={last_n}")
                    continue
                last_mean = run_scenario(out, name, "keyset", fn, arrays[n], keys[n], n, args.reps)
                last_n = n
            arr = arrays[position_n]
            for scen, idx in (("pos_start", 0), ("pos_center", position_n // 2), ("pos_end", position_n - 1)):
                run_scenario(out, name, scen, fn, arr, [arr[idx]] * POSITION_REPEATS, position_n, args.reps)
    finally:
        out.close()
    print(f"Done -> {args.out}")


if __name__ == "__main__":
    main()
