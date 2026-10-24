"""Builds the LaTeX tables and figure folder used by report/overleaf/main.tex.

Reads the CSV files of the two machines (results/ -> machine A, resultsv2/ -> machine B), writes one .tex
fragment per table into report/overleaf/tables/ and copies the figures into report/overleaf/figs/.
Usage: python tools/make_latex.py [--stats]
"""
import argparse
import csv
import glob
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "report" / "overleaf"
MACHINES = {"A": ("results", "figures"), "B": ("resultsv2", "figuresv2")}
LANGS = ["Java", "Python"]
SIZES = [1_000, 10_000, 100_000, 1_000_000]
SORT_ALGOS = ["InsertionSort", "DualPivotQuickSort", "MergeSort", "HeapSort", "RadixSort", "BucketSort"]
SORT_LABEL = {"InsertionSort": "Insertion Sort", "DualPivotQuickSort": "Dual-Pivot QuickSort",
              "MergeSort": "Merge Sort", "HeapSort": "Heap Sort", "RadixSort": "Radix Sort",
              "BucketSort": "Bucket Sort"}
SEARCH_ALGOS = ["Linear", "Binary", "Ternary", "Jump", "Interpolation", "Exponential"]
SEARCH_LABEL = {"Linear": "Lineal", "Binary": "Binaria", "Ternary": "Ternaria", "Jump": "Por saltos",
                "Interpolation": "Interpolaci\\'on", "Exponential": "Exponencial"}
VARIANT_LABEL = {"random": "Aleatoria", "asc": "Ascendente", "desc": "Descendente"}
POS = [("pos_start", "Inicio"), ("pos_center", "Centro"), ("pos_end", "Final")]


# ------------------------------------------------------------------------------------------------ data
def load(machine):
    res_dir = ROOT / MACHINES[machine][0]
    rows = {}
    for kind in ("sort", "search"):
        for lang in LANGS:
            files = glob.glob(str(res_dir / f"{kind}_{lang.lower()}*.csv"))
            if len(files) != 1:
                sys.exit(f"expected exactly one {kind}_{lang.lower()}*.csv in {res_dir}, found {files}")
            with open(files[0], encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    scen = r.get("variant") or r.get("scenario")
                    r["n"] = int(r["n"])
                    r["mean_s"] = float(r["mean_s"])
                    r["std_s"] = float(r["std_s"]) if r["std_s"].strip() else float("nan")
                    r["measured"] = r["measured"].strip().lower() == "true"
                    rows[(kind, lang, r["algorithm"], scen, r["n"])] = r
    return rows


# ------------------------------------------------------------------------------------------ formatting
def dec(x, digits=3):
    s = f"{x:.{digits}g}"
    if "e" in s:
        s = f"{x:.{digits}f}"
    return s.replace(".", ",")


def unit(t):
    for lim, scale, name in ((1e-6, 1e-9, "ns"), (1e-3, 1e-6, "$\\mu$s"), (1, 1e-3, "ms"), (60, 1.0, "s"),
                             (3600, 60.0, "min")):
        if t < lim:
            return scale, name
    return 3600.0, "h"


def fmt_time(t):
    scale, name = unit(t)
    return f"{dec(t / scale)} {name}"


def fmt_cell(r):
    if r is None:
        return "n/d"
    if not r["measured"]:
        return f"$\\sim$\\,{fmt_time(r['mean_s'])}\\,(est.)"
    scale, name = unit(r["mean_s"])
    return f"{dec(r['mean_s'] / scale)} $\\pm$ {dec(r['std_s'] / scale, 2)} {name}"


def thousands(n):
    return f"{n:,}".replace(",", ".")


def cost_model(kind, alg, scen):
    nlogn = lambda n: n * math.log2(n)  # noqa: E731
    quad = lambda n: float(n) ** 2  # noqa: E731
    if kind == "sort":
        if alg == "InsertionSort":
            return (lambda n: float(n)) if scen == "asc" else quad
        if alg == "DualPivotQuickSort":
            return nlogn if scen == "random" else quad
        if alg in ("MergeSort", "HeapSort"):
            return nlogn
        return lambda n: float(n)
    return {"Linear": float, "Binary": math.log2, "Ternary": math.log2, "Jump": math.sqrt,
            "Interpolation": lambda n: math.log2(math.log2(n)), "Exponential": math.log2}[alg]


def table(colspec, header, body, size="\\small"):
    lines = [f"{{{size}", f"\\begin{{tabular}}{{{colspec}}}", "\\toprule", " & ".join(header) + " \\\\",
             "\\midrule"]
    lines += [" & ".join(row) + " \\\\" for row in body]
    lines += ["\\bottomrule", "\\end{tabular}}\\par"]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------- tables
def growth_table(rows):
    hdr = ["Algoritmo"] + [f"{thousands(a)} $\\to$ {thousands(b)}" for a, b in zip(SIZES, SIZES[1:])]
    out = ""
    for lang in LANGS:
        body = []
        for alg in SORT_ALGOS:
            cost = cost_model("sort", alg, "random")
            row = [SORT_LABEL[alg]]
            for a, b in zip(SIZES, SIZES[1:]):
                ra, rb = rows[("sort", lang, alg, "random", a)], rows[("sort", lang, alg, "random", b)]
                mark = "" if ra["measured"] and rb["measured"] else "$\\sim$"
                row.append(f"{mark}$\\times${dec(rb['mean_s'] / ra['mean_s'], 3)} "
                           f"(te\\'or. $\\times${dec(cost(b) / cost(a), 3)})")
            body.append(row)
        out += f"\\textbf{{{lang}}}\\par\\smallskip\n" + table("lccc", hdr, body, "\\footnotesize") + "\\medskip\n"
    return out


def search_growth_table(rows):
    hdr = ["Algoritmo"] + [f"{thousands(a)} $\\to$ {thousands(b)}" for a, b in zip(SIZES, SIZES[1:])]
    out = ""
    for lang in LANGS:
        body = []
        for alg in SEARCH_ALGOS:
            cost = cost_model("search", alg, "keyset")
            row = [SEARCH_LABEL[alg]]
            for a, b in zip(SIZES, SIZES[1:]):
                ra, rb = rows[("search", lang, alg, "keyset", a)], rows[("search", lang, alg, "keyset", b)]
                row.append(f"$\\times${dec(rb['mean_s'] / ra['mean_s'], 3)} "
                           f"(te\\'or. $\\times${dec(cost(b) / cost(a), 3)})")
            body.append(row)
        out += f"\\textbf{{{lang}}}\\par\\smallskip\n" + table("lccc", hdr, body, "\\footnotesize") + "\\medskip\n"
    return out


def position_table(rows, lang):
    body = []
    for alg in SEARCH_ALGOS:
        body.append([SEARCH_LABEL[alg]] + [fmt_cell(rows[("search", lang, alg, p, 1_000_000)]) for p, _ in POS])
    return table("lrrr", ["Algoritmo"] + [lbl for _, lbl in POS], body)


def q1_table(rows):
    body = []
    for alg in SORT_ALGOS:
        kind = "No comparativo" if alg in ("RadixSort", "BucketSort") else "Comparativo"
        body.append([SORT_LABEL[alg], kind] + [fmt_cell(rows[("sort", lg, alg, "random", 1_000_000)])
                                              for lg in LANGS])
    return table("llrr", ["Algoritmo", "Tipo", "Java", "Python"], body)


def q2_numbers(rows):
    out = {}
    for lang in LANGS:
        cands = [(rows[("sort", lang, a, "random", 1_000_000)]["mean_s"], a) for a in SORT_ALGOS
                 if rows[("sort", lang, a, "random", 1_000_000)]["measured"]]
        t_sort, best = min(cands)
        t_lin = rows[("search", lang, "Linear", "keyset", 1_000_000)]["mean_s"]
        t_bin = rows[("search", lang, "Binary", "keyset", 1_000_000)]["mean_s"]
        out[lang] = {"alg": best, "t_sort": t_sort, "t_lin": t_lin, "t_bin": t_bin,
                     "k": t_sort / (t_lin - t_bin)}
    return out


def q2_table(all_rows):
    body = []
    for m, rows in all_rows.items():
        for lang, v in q2_numbers(rows).items():
            body.append([m, lang, SORT_LABEL[v["alg"]], fmt_time(v["t_sort"]), fmt_time(v["t_lin"]),
                         fmt_time(v["t_bin"]), f"{dec(v['k'], 4)} $\\Rightarrow$ {math.ceil(v['k'])}"])
    return table("llllrrr", ["Equipo", "Lenguaje", "Mejor ordenamiento", "$T_{\\text{orden}}$",
                             "$t_{\\text{lineal}}$", "$t_{\\text{binaria}}$", "$k^*$"], body, "\\footnotesize")


def full_sort_table(rows, lang):
    body = []
    for alg in SORT_ALGOS:
        for v in ("random", "asc", "desc"):
            body.append([SORT_LABEL[alg] if v == "random" else "", VARIANT_LABEL[v]] +
                        [fmt_cell(rows[("sort", lang, alg, v, n)]) for n in SIZES])
    return table("llrrrr", ["Algoritmo", "Entrada"] + [f"$n={thousands(n)}$" for n in SIZES], body,
                 "\\scriptsize")


def full_search_table(rows, lang):
    body = [[SEARCH_LABEL[a]] + [fmt_cell(rows[("search", lang, a, "keyset", n)]) for n in SIZES]
            for a in SEARCH_ALGOS]
    return table("lrrrr", ["Algoritmo"] + [f"$n={thousands(n)}$" for n in SIZES], body, "\\scriptsize")


def cross_table(all_rows):
    """Ratio machine B / machine A at n = 1.000.000 (>1 means B is slower)."""
    a, b = all_rows["A"], all_rows["B"]
    body = []
    for kind, algos, labels, scen, title in (("sort", SORT_ALGOS, SORT_LABEL, "random", "Ordenamiento (aleatoria)"),
                                             ("search", SEARCH_ALGOS, SEARCH_LABEL, "keyset", "B\\'usqueda (1.000 claves)")):
        body.append([f"\\multicolumn{{3}}{{l}}{{\\textit{{{title}}}}}"])
        for alg in algos:
            row = [labels[alg]]
            for lang in LANGS:
                ra, rb = a[(kind, lang, alg, scen, 1_000_000)], b[(kind, lang, alg, scen, 1_000_000)]
                mark = "" if ra["measured"] and rb["measured"] else "$\\sim$"
                row.append(f"{mark}$\\times${dec(rb['mean_s'] / ra['mean_s'], 3)}")
            body.append(row)
    return table("lrr", ["Algoritmo", "Java", "Python"], body)


def tex_escape(s):
    return s.replace("_", "\\_").replace("%", "\\%").replace("&", "\\&").replace(">", "$>$")


def issues_table(rows):
    body = []
    for key in sorted(rows, key=lambda k: (k[1], k[2], k[3], k[4], k[0])):
        r = rows[key]
        if not r["measured"] or r["status"] != "OK":
            body.append([r["language"], r["algorithm"], r.get("variant") or r.get("scenario"), thousands(r["n"]),
                         tex_escape(r["status"]), tex_escape(r["note"])])
    return table("lllrlp{4.6cm}", ["Lenguaje", "Algoritmo", "Entrada", "$n$", "Estado", "Nota"], body, "\\tiny")


# ------------------------------------------------------------------------------------------- stats
def print_stats(all_rows):
    for m, rows in all_rows.items():
        print(f"\n######## Machine {m}")
        for lang in LANGS:
            print(f"-- sort random 1e6 ({lang}):", {a: round(rows[('sort', lang, a, 'random', 1_000_000)]['mean_s'], 4)
                                                       for a in SORT_ALGOS})
        for alg in SORT_ALGOS:
            j, p = (rows[("sort", lg, alg, "random", 1_000_000)] for lg in LANGS)
            print(f"   Python/Java {alg:<20} x{p['mean_s'] / j['mean_s']:.1f}"
                  f"{'  (python est.)' if not p['measured'] else ''}")
        for alg in SEARCH_ALGOS:
            j, p = (rows[("search", lg, alg, "keyset", 1_000_000)] for lg in LANGS)
            print(f"   Python/Java search {alg:<14} x{p['mean_s'] / j['mean_s']:.1f}")
        for n in (1_000, 10_000, 100_000):
            for alg in SORT_ALGOS:
                r0 = rows[("sort", "Java", alg, "random", n)]["mean_s"]
                a = rows[("sort", "Java", alg, "asc", n)]["mean_s"]
                d = rows[("sort", "Java", alg, "desc", n)]["mean_s"]
                print(f"   order n={n:<6} {alg:<20} asc/rand={a / r0:8.3f} desc/rand={d / r0:8.3f}")
        for lang, v in q2_numbers(rows).items():
            print(f"   k* {lang}: {v}")
    print("\n######## Machine B / Machine A")
    for kind, algos, scen in (("sort", SORT_ALGOS, "random"), ("search", SEARCH_ALGOS, "keyset")):
        for lang in LANGS:
            print(f"-- {kind} {lang}:", {a: round(all_rows['B'][(kind, lang, a, scen, 1_000_000)]['mean_s'] /
                                                  all_rows['A'][(kind, lang, a, scen, 1_000_000)]['mean_s'], 2)
                                         for a in algos})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    all_rows = {m: load(m) for m in MACHINES}
    if args.stats:
        print_stats(all_rows)
        return
    tdir, fdir = OUT / "tables", OUT / "figs"
    tdir.mkdir(parents=True, exist_ok=True)
    fdir.mkdir(parents=True, exist_ok=True)

    def w(name, text):
        (tdir / f"{name}.tex").write_text(text, encoding="utf-8")

    for m, rows in all_rows.items():
        w(f"growth_{m}", growth_table(rows))
        w(f"search_growth_{m}", search_growth_table(rows))
        for lang in LANGS:
            w(f"pos_{m}_{lang.lower()}", position_table(rows, lang))
            w(f"full_sort_{m}_{lang.lower()}", full_sort_table(rows, lang))
            w(f"full_search_{m}_{lang.lower()}", full_search_table(rows, lang))
        w(f"q1_{m}", q1_table(rows))
        w(f"issues_{m}", issues_table(rows))
        for png in sorted((ROOT / "report" / MACHINES[m][1]).glob("*.png")):
            shutil.copyfile(png, fdir / f"{m}_{png.name}")
    w("q2", q2_table(all_rows))
    w("cross", cross_table(all_rows))
    print(f"wrote {len(list(tdir.glob('*.tex')))} tables and {len(list(fdir.glob('*.png')))} figures to {OUT}")


if __name__ == "__main__":
    main()
