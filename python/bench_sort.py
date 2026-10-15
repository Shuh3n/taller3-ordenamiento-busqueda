#!/usr/bin/env python3
"""Point 1 benchmark (Python).

Usage: python python/bench_sort.py [--data data] [--out results/sort_python.csv]
                                   [--max-n 1000000] [--reps 5] [--limit-seconds 300]
"""
import argparse
import operator
import os
import sys
import time

import sorting
from common import SIZES, CsvOut, load_ints, mean_std, predict, sort_model

VARIANTS = ["random", "asc", "desc"]
ALGOS = {
    "InsertionSort": sorting.insertion_sort,
    "DualPivotQuickSort": sorting.dual_pivot_quick_sort,
    "MergeSort": sorting.merge_sort,
    "HeapSort": sorting.heap_sort,
    "RadixSort": sorting.radix_sort,
    "BucketSort": sorting.bucket_sort,
}


def is_sorted(a):
    return all(map(operator.le, a, a[1:]))


def run_series(out, name, fn, variant, sizes, data, reps, limit):
    cost = sort_model(name, variant)
    last_mean, last_n, failed = None, 0, False
    for n in sizes:
        base = data[(variant, n)]
        est = predict(last_mean, last_n, cost, n)
        if failed:
            out.row(name, variant, n, None, est, None, False, "ESTIMATED",
                    f"same failure expected (recursion depth grows with n); scaled from n={last_n}")
            continue
        if est is not None and est > limit:
            out.row(name, variant, n, None, est, None, False, "ESTIMATED",
                    f"predicted {est:.0f}s > limit {limit:.0f}s; scaled from n={last_n}")
            continue
        try:
            times, ok, total = [], True, sum(base)
            for _ in range(reps):
                a = base[:]  # fresh copy per repetition, not timed
                t0 = time.perf_counter_ns()
                fn(a)
                t1 = time.perf_counter_ns()
                times.append((t1 - t0) / 1e9)
                ok = ok and is_sorted(a) and sum(a) == total  # verification, not timed
            mean, std = mean_std(times)
            out.row(name, variant, n, times, mean, std, True, "OK" if ok else "VERIFICATION_FAILED")
            last_mean, last_n = mean, n
            print(f"{name:<20} {variant:<7} n={n:<8} mean={mean:.6f}s", flush=True)
        except RecursionError:
            failed = True
            out.row(name, variant, n, None, est, None, False, "ERROR_RecursionError",
                    f"RecursionError at n={n} (limit {sys.getrecursionlimit()}); scaled from n={last_n}")
            print(f"{name:<20} {variant:<7} n={n:<8} RecursionError", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="results/sort_python.csv")
    ap.add_argument("--max-n", type=int, default=1_000_000)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--limit-seconds", type=float, default=300.0)
    ap.add_argument("--recursion-limit", type=int, default=None,
                    help="override Python's recursion limit (default: leave the interpreter default)")
    args = ap.parse_args()
    if args.recursion_limit:
        sys.setrecursionlimit(args.recursion_limit)

    sizes = [n for n in SIZES if n <= args.max_n]
    # Data is read BEFORE any measurement; file I/O is never timed.
    data = {(v, n): load_ints(os.path.join(args.data, f"{v}_{n}.txt")) for n in sizes for v in VARIANTS}

    out = CsvOut(args.out, "variant", args.reps)
    try:
        for name, fn in ALGOS.items():
            for variant in VARIANTS:
                run_series(out, name, fn, variant, sizes, data, args.reps, args.limit_seconds)
    finally:
        out.close()
    print(f"Done -> {args.out}")


if __name__ == "__main__":
    main()
