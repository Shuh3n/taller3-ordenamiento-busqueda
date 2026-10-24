#!/usr/bin/env python3
"""Run the whole workshop pipeline, one step after another (never in parallel).

  python run_all.py                     full run (can take hours)
  python run_all.py --quick             smoke test: n <= 10,000, 2 repetitions, output in smoke/
  python run_all.py --steps sort_python,search_python   run only some steps

Steps, in order: data, compile, sort_java, sort_python, search_java, search_python, figures.
Output: CSV files in results/ and PNG figures in report/figures/ (nothing else).
The script stops at the first failing step and tells you how to resume from it.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JAVA_SRC = [f"java/src/{n}.java" for n in
            ("Util", "SortAlgorithms", "SearchAlgorithms", "BenchSort", "BenchSearch")]
STEP_ORDER = ["data", "compile", "sort_java", "sort_python", "search_java", "search_python", "figures"]


def fmt(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"


def build_steps(quick):
    py = sys.executable

    def extra(name):
        return ["--max-n", "10000", "--reps", "2", "--out", f"smoke/{name}"] if quick else []

    return {
        "data": [py, "tools/generate_data.py"],
        "compile": ["javac", "-d", "java/out", *JAVA_SRC],
        "sort_java": ["java", "-cp", "java/out", "BenchSort", *extra("sort_java.csv")],
        "sort_python": [py, "python/bench_sort.py", *extra("sort_python.csv")],
        "search_java": ["java", "-cp", "java/out", "BenchSearch", *extra("search_java.csv")],
        "search_python": [py, "python/bench_search.py", *extra("search_python.csv")],
        "figures": [py, "tools/make_figures.py"],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="smoke test (small n, 2 reps, output in smoke/)")
    ap.add_argument("--steps", default="", help="comma-separated subset of: " + ", ".join(STEP_ORDER))
    args = ap.parse_args()

    wanted = [s.strip() for s in args.steps.split(",") if s.strip()] or list(STEP_ORDER)
    unknown = [s for s in wanted if s not in STEP_ORDER]
    if unknown:
        sys.exit(f"Unknown step(s): {', '.join(unknown)}. Valid: {', '.join(STEP_ORDER)}")
    if args.quick and "figures" in wanted and not args.steps:
        wanted.remove("figures")  # the figures read results/, not smoke/
    wanted = [s for s in STEP_ORDER if s in wanted]

    commands = build_steps(args.quick)
    for tool in ("javac", "java"):
        if shutil.which(tool) is None and any(commands[s][0] == tool for s in wanted):
            sys.exit(f"'{tool}' was not found in PATH. Install a JDK (17+) and open a new terminal.")

    total = time.time()
    for i, step in enumerate(wanted, 1):
        print(f"\n===== [{i}/{len(wanted)}] {step}: {' '.join(commands[step])}", flush=True)
        t0 = time.time()
        if subprocess.run(commands[step], cwd=ROOT).returncode != 0:
            rest = ",".join(s for s in STEP_ORDER if STEP_ORDER.index(s) >= STEP_ORDER.index(step))
            sys.exit(f"\nStep '{step}' failed. Fix the problem and resume with:\n"
                     f"  python run_all.py --steps {rest}")
        print(f"----- {step} finished in {fmt(time.time() - t0)}", flush=True)
    print(f"\nAll done in {fmt(time.time() - total)}.")
    if args.quick:
        print("Quick results are in smoke/ (do not use them for the report).")
    elif "figures" in wanted:
        print("Results: results/*.csv   Figures: report/figures/*.png")


if __name__ == "__main__":
    main()
