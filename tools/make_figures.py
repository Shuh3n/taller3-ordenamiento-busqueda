#!/usr/bin/env python3
"""Build the figures of the report from the CSV results.

Usage: python tools/make_figures.py [--results results] [--out report/figures]

Writes p1_growth_*, p1_order_*, p1_compiled, p2_growth_*, p2_compiled and p3_q2 as PNG files.
"""
import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
from common import SIZES  # noqa: E402

NAN = float("nan")
LANGS = ["Java", "Python"]
SORT_ALGOS = ["InsertionSort", "DualPivotQuickSort", "MergeSort", "HeapSort", "RadixSort", "BucketSort"]
SORT_LABEL = {"InsertionSort": "Insertion Sort", "DualPivotQuickSort": "Dual-Pivot QuickSort",
              "MergeSort": "Merge Sort", "HeapSort": "Heap Sort", "RadixSort": "Radix Sort",
              "BucketSort": "Bucket Sort"}
SEARCH_ALGOS = ["Linear", "Binary", "Ternary", "Jump", "Interpolation", "Exponential"]
SEARCH_LABEL = {"Linear": "Lineal", "Binary": "Binaria", "Ternary": "Ternaria", "Jump": "Por saltos",
                "Interpolation": "Interpolación", "Exponential": "Exponencial"}
VARIANT_LABEL = {"random": "Aleatoria", "asc": "Ascendente", "desc": "Descendente"}
PAL = [plt.get_cmap("tab10")(i) for i in range(10)]


# ----------------------------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------------------------
def _f(s):
    s = (s or "").strip()
    return float(s) if s and s.lower() != "nan" else NAN


class Results:
    def __init__(self, results_dir):
        self.rows = {}
        found = False
        for kind in ("sort", "search"):
            for lang in LANGS:
                path = results_dir / f"{kind}_{lang.lower()}.csv"
                if not path.exists():
                    print(f"[warn] missing {path}")
                    continue
                found = True
                with open(path, encoding="utf-8", newline="") as fh:
                    for r in csv.DictReader(fh):
                        scen = r.get("variant") or r.get("scenario")
                        r["n"] = int(r["n"])
                        r["mean_s"] = _f(r["mean_s"])
                        r["measured"] = r["measured"].strip().lower() == "true"
                        self.rows.setdefault((kind, lang, r["algorithm"], scen), {})[r["n"]] = r
        if not found:
            sys.exit("No result CSV files found. Run the benchmarks first (see README.md).")

    def val(self, kind, lang, alg, scen, n):
        r = self.rows.get((kind, lang, alg, scen), {}).get(n)
        return (r["mean_s"], r["measured"]) if r else (NAN, False)

    def sizes(self):
        return sorted({n for series in self.rows.values() for n in series})


# ----------------------------------------------------------------------------------------------
# Formatting and figures
# ----------------------------------------------------------------------------------------------
def thousands(n):
    return f"{n:,}".replace(",", ".")


def _unit(t):
    if t < 1e-6:
        return 1e-9, "ns"
    if t < 1e-3:
        return 1e-6, "µs"
    if t < 1:
        return 1e-3, "ms"
    if t < 60:
        return 1.0, "s"
    if t < 3600:
        return 60.0, "min"
    return 3600.0, "h"


def fmt_time(t):
    if t != t:
        return "n/d"
    scale, unit = _unit(t)
    return f"{t / scale:.3g} {unit}"


def _style(ax, xlabel, ylabel, title):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    ax.grid(True, which="both", alpha=0.25)


def growth_figure(res, kind, lang, algos, labels, scen, path, title, ylabel):
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    drawn = False
    for i, alg in enumerate(algos):
        pts = []
        for n in SIZES:
            v, m = res.val(kind, lang, alg, scen, n)
            if v == v and v > 0:
                pts.append((n, v, m))
        if not pts:
            continue
        drawn = True
        xs, ys, ms = [p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts]
        c = PAL[i]
        ax.plot(xs, ys, ls="--", color=c, lw=1.1)
        for a in range(len(xs) - 1):
            if ms[a] and ms[a + 1]:
                ax.plot(xs[a:a + 2], ys[a:a + 2], ls="-", color=c, lw=2)
        ax.plot([x for x, m in zip(xs, ms) if m], [y for y, m in zip(ys, ms) if m],
                ls="none", marker="o", color=c, label=labels[alg])
        ax.plot([x for x, m in zip(xs, ms) if not m], [y for y, m in zip(ys, ms) if not m],
                ls="none", marker="o", mfc="white", color=c)
    if not drawn:
        plt.close(fig)
        return False
    ax.set_xscale("log")
    ax.set_yscale("log")
    _style(ax, "n (número de elementos)", ylabel, title)
    handles, _ = ax.get_legend_handles_labels()
    handles += [Line2D([], [], color="gray", ls="-", marker="o", label="Medido"),
                Line2D([], [], color="gray", ls="--", marker="o", mfc="white", label="Estimado")]
    ax.legend(handles=handles, fontsize=7.5, loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return True


def bar_figure(path, groups, series, title, ylabel):
    """series: list of (label, [(value, measured) for each group])."""
    values = [v for _, vals in series for v, _m in vals if v == v and v > 0]
    if not values:
        return False
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.set_yscale("log")
    ymin, ymax = min(values) / 3, max(values) * 14
    ax.set_ylim(ymin, ymax)
    k = len(series)
    w = 0.8 / k
    for si, (label, vals) in enumerate(series):
        for gi, (v, m) in enumerate(vals):
            if not (v == v and v > 0):
                continue
            x = gi + (si - (k - 1) / 2) * w
            ax.bar(x, v - ymin, w * 0.92, bottom=ymin, color=PAL[si], hatch=None if m else "///",
                   edgecolor="black" if not m else PAL[si], linewidth=0.6)
            ax.text(x, v * 1.12, ("" if m else "~") + fmt_time(v), ha="center", va="bottom",
                    rotation=90, fontsize=6.5)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups, fontsize=8, rotation=15, ha="right")
    _style(ax, "", ylabel, title)
    handles = [Patch(color=PAL[i], label=lbl) for i, (lbl, _) in enumerate(series)]
    handles.append(Patch(facecolor="white", edgecolor="black", hatch="///", label="Estimado"))
    ax.legend(handles=handles, fontsize=7.5, loc="upper left", ncol=min(4, len(handles)))
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=str(ROOT / "report" / "figures"))
    args = ap.parse_args()
    fig_dir = Path(args.out)
    fig_dir.mkdir(parents=True, exist_ok=True)

    res = Results(Path(args.results))
    sizes = [n for n in SIZES if n in res.sizes()]
    big = sizes[-1]
    written = []

    def fig(name, ok):
        if ok:
            written.append(name)

    for lang in LANGS:
        n = f"p1_growth_{lang.lower()}"
        fig(n, growth_figure(res, "sort", lang, SORT_ALGOS, SORT_LABEL, "random", fig_dir / f"{n}.png",
                             f"Ordenamiento ({lang}) - entrada aleatoria", "Tiempo (s)"))
    for n_ in [x for x in (1_000, 10_000, 100_000) if x in sizes]:
        series = [(VARIANT_LABEL[v], [res.val("sort", "Java", a, v, n_) for a in SORT_ALGOS])
                  for v in ("random", "asc", "desc")]
        name = f"p1_order_{n_}"
        fig(name, bar_figure(fig_dir / f"{name}.png", [SORT_LABEL[a] for a in SORT_ALGOS], series,
                             f"Efecto del orden de entrada (Java, n = {thousands(n_)})", "Tiempo (s)"))
    series = [(lang, [res.val("sort", lang, a, "random", big) for a in SORT_ALGOS]) for lang in LANGS]
    fig("p1_compiled", bar_figure(fig_dir / "p1_compiled.png", [SORT_LABEL[a] for a in SORT_ALGOS], series,
                                  f"Compilado vs interpretado (n = {thousands(big)}, aleatoria)", "Tiempo (s)"))
    for lang in LANGS:
        n = f"p2_growth_{lang.lower()}"
        fig(n, growth_figure(res, "search", lang, SEARCH_ALGOS, SEARCH_LABEL, "keyset", fig_dir / f"{n}.png",
                             f"Búsqueda ({lang}) - 1.000 claves", "Tiempo promedio por búsqueda (s)"))
    series = [(lang, [res.val("search", lang, a, "keyset", big) for a in SEARCH_ALGOS]) for lang in LANGS]
    fig("p2_compiled", bar_figure(fig_dir / "p2_compiled.png", [SEARCH_LABEL[a] for a in SEARCH_ALGOS], series,
                                  f"Compilado vs interpretado (n = {thousands(big)})",
                                  "Tiempo promedio por búsqueda (s)"))

    # Ordenar o no ordenar: k* = T_orden / (t_lineal - t_binaria), best *measured* sort at the largest n
    q2 = {}
    for lang in LANGS:
        cands = [(res.val("sort", lang, a, "random", big)[0], a) for a in SORT_ALGOS
                 if res.val("sort", lang, a, "random", big)[1]]
        t_lin, _ = res.val("search", lang, "Linear", "keyset", big)
        t_bin, _ = res.val("search", lang, "Binary", "keyset", big)
        if cands and t_lin == t_lin and t_bin == t_bin and t_lin > t_bin:
            t_sort, best = min(cands)
            q2[lang] = {"alg": best, "t_sort": t_sort, "t_lin": t_lin, "t_bin": t_bin,
                        "k_star": t_sort / (t_lin - t_bin)}
    if q2:
        fig_q, ax = plt.subplots(figsize=(7.2, 4.2))
        ks = [10 ** (i / 10) for i in range(0, 61)]
        for i, (lang, d) in enumerate(q2.items()):
            ax.plot(ks, [k * d["t_lin"] for k in ks], color=PAL[i], ls="--", label=f"{lang}: k búsquedas lineales")
            ax.plot(ks, [d["t_sort"] + k * d["t_bin"] for k in ks], color=PAL[i],
                    label=f"{lang}: ordenar + k binarias")
            ax.axvline(d["k_star"], color=PAL[i], ls=":", lw=1)
            print(f"k* ({lang}, {SORT_LABEL[d['alg']]}): {d['k_star']:.1f}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        _style(ax, "k (número de búsquedas)", "Tiempo total (s)", f"Ordenar o no ordenar (n = {thousands(big)})")
        ax.legend(fontsize=7.5)
        fig_q.tight_layout()
        fig_q.savefig(fig_dir / "p3_q2.png", dpi=170)
        plt.close(fig_q)
        written.append("p3_q2")
    print(f"{len(written)} figures written to {fig_dir}")


if __name__ == "__main__":
    main()
