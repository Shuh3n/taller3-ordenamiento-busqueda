#!/usr/bin/env python3
"""Generate the shared test data once (fixed seed, plain-text files, one integer per line).

For every size n it writes:
  random_<n>.txt  unsorted array of 8-digit integers
  asc_<n>.txt     the same values sorted ascending
  desc_<n>.txt    the same values sorted descending
  keys_<n>.txt    1,000 search keys (500 present in the array, 500 absent), shuffled
"""
import argparse
from pathlib import Path

import numpy as np

SIZES = [1_000, 10_000, 100_000, 1_000_000]
LOW, HIGH = 10_000_000, 99_999_999  # 8-digit integers, both ends inclusive
N_KEYS = 1_000


def write_ints(path, values):
    with open(path, "w", newline="\n", encoding="utf-8") as f:
        f.write("\n".join(map(str, values.tolist())))
        f.write("\n")


def make_keys(rng, arr):
    half = N_KEYS // 2
    present = arr[rng.choice(len(arr), size=half, replace=False)]
    present_set = set(arr.tolist())
    absent, seen = [], set()
    while len(absent) < half:
        for c in rng.integers(LOW, HIGH + 1, size=half * 2).tolist():
            if c not in present_set and c not in seen:
                seen.add(c)
                absent.append(c)
                if len(absent) == half:
                    break
    keys = np.concatenate([present, np.array(absent, dtype=arr.dtype)])
    return rng.permutation(keys)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data", help="output directory (default: data)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    for n in SIZES:
        arr = rng.integers(LOW, HIGH + 1, size=n, dtype=np.int64)
        asc = np.sort(arr)
        write_ints(out / f"random_{n}.txt", arr)
        write_ints(out / f"asc_{n}.txt", asc)
        write_ints(out / f"desc_{n}.txt", asc[::-1])
        write_ints(out / f"keys_{n}.txt", make_keys(rng, arr))
        print(f"n={n:>9,}: wrote random/asc/desc/keys files in {out}/")


if __name__ == "__main__":
    main()
