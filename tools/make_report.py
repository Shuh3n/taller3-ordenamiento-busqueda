#!/usr/bin/env python3
"""Build the figures, the tables and the final PDF from the CSV results.

Usage: python tools/make_report.py [--results results] [--out report]

Narrative analysis is read from report/analysis/<key>.md (plain text, blank line = new paragraph,
"- " = bullet, **bold** supported). A file whose text starts with PENDIENTE is rendered in red so
that unfinished sections are impossible to miss. Group data lives in report/meta.json.
"""
import argparse
import csv
import html
import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (KeepTogether, Image, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
from common import SIZES, search_model, sort_model  # noqa: E402

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
POS_LABEL = {"pos_start": "Inicio", "pos_center": "Centro", "pos_end": "Final"}
PAL = [plt.get_cmap("tab10")(i) for i in range(10)]

GFG = "https://www.geeksforgeeks.org/"
SOURCES = [
    ("Insertion Sort", "insertion-sort-algorithm/"), ("Dual-Pivot QuickSort", "dual-pivot-quicksort/"),
    ("Merge Sort", "merge-sort/"), ("Heap Sort", "heap-sort/"), ("Radix Sort", "radix-sort/"),
    ("Bucket Sort", "bucket-sort-2/"), ("Búsqueda lineal", "linear-search/"),
    ("Búsqueda binaria", "binary-search/"), ("Búsqueda ternaria", "ternary-search/"),
    ("Búsqueda por saltos", "jump-search/"), ("Búsqueda por interpolación", "interpolation-search/"),
    ("Búsqueda exponencial", "exponential-search/"),
]


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
                        r["std_s"] = _f(r["std_s"])
                        r["measured"] = r["measured"].strip().lower() == "true"
                        self.rows.setdefault((kind, lang, r["algorithm"], scen), {})[r["n"]] = r
        if not found:
            sys.exit("No result CSV files found. Run the benchmarks first (see README.md).")

    def get(self, kind, lang, alg, scen, n):
        return self.rows.get((kind, lang, alg, scen), {}).get(n)

    def val(self, kind, lang, alg, scen, n):
        r = self.get(kind, lang, alg, scen, n)
        return (r["mean_s"], r["measured"]) if r else (NAN, False)

    def sizes(self):
        return sorted({n for series in self.rows.values() for n in series})

    def all_rows(self):
        for series in self.rows.values():
            yield from series.values()


# ----------------------------------------------------------------------------------------------
# Formatting
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


def fmt_pm(mean, std, measured):
    if mean != mean:
        return "n/d"
    if not measured:
        return "~" + fmt_time(mean) + " (est.)"
    scale, unit = _unit(mean)
    return f"{mean / scale:.3g} ± {std / scale:.2g} {unit}"


# ----------------------------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------------------------
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


# ----------------------------------------------------------------------------------------------
# Tables (reportlab)
# ----------------------------------------------------------------------------------------------
def make_table(rows, widths, styles, font=7.5, header=True):
    cell = ParagraphStyle("cell", parent=styles["body"], fontSize=font, leading=font + 2, alignment=0)
    cellb = ParagraphStyle("cellb", parent=cell, fontName="DV-B")
    data = []
    for ri, row in enumerate(rows):
        data.append([Paragraph(html.escape(str(c)), cellb if (header and ri == 0) else cell) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4") if header else colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def results_table(res, kind, lang, algos, labels, scen, sizes, styles):
    rows = [["Algoritmo"] + [f"n = {thousands(n)}" for n in sizes]]
    for alg in algos:
        row = [labels[alg]]
        for n in sizes:
            r = res.get(kind, lang, alg, scen, n)
            row.append(fmt_pm(r["mean_s"], r["std_s"], r["measured"]) if r else "n/d")
        rows.append(row)
    first = 3.6 * cm
    other = (17 * cm - first) / len(sizes)
    return make_table(rows, [first] + [other] * len(sizes), styles)


# ----------------------------------------------------------------------------------------------
# Narrative helpers
# ----------------------------------------------------------------------------------------------
def inline(text):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(text, quote=False))


def narrative(path, styles):
    if not path.exists():
        return [Paragraph(f"PENDIENTE: falta el archivo {path.name}.", styles["pending"])]
    text = path.read_text(encoding="utf-8").strip()
    pending = text.upper().startswith("PENDIENTE")
    body = styles["pending"] if pending else styles["body"]
    out = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if lines and all(ln.lstrip().startswith("- ") for ln in lines):
            for ln in lines:
                out.append(Paragraph(inline(ln.lstrip()[2:]), body, bulletText="•"))
        else:
            out.append(Paragraph(inline(" ".join(lines)), body))
    return out


def environment():
    info = {"Sistema": platform.platform(), "Procesador": platform.processor() or platform.machine(),
            "Python": platform.python_version(), "Java": "n/d"}
    try:
        out = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=20)
        info["Java"] = (out.stderr or out.stdout).splitlines()[0].strip()
    except Exception:  # noqa: BLE001
        pass
    return info


# ----------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=str(ROOT / "report"))
    args = ap.parse_args()
    results_dir, out_dir = Path(args.results), Path(args.out)
    fig_dir, ana_dir = out_dir / "figures", out_dir / "analysis"
    fig_dir.mkdir(parents=True, exist_ok=True)
    ana_dir.mkdir(parents=True, exist_ok=True)

    res = Results(results_dir)
    sizes = [n for n in SIZES if n in res.sizes()]
    big = sizes[-1]
    meta = {"title": "Taller 3: Ordenamiento y Búsqueda", "course": "", "members": [], "repo_url": "", "date": ""}
    meta_path = out_dir / "meta.json"
    if meta_path.exists():
        meta.update(json.loads(meta_path.read_text(encoding="utf-8")))

    # ---- Figures ---------------------------------------------------------------------------
    figs = {}

    def fig(name, ok):
        figs[name] = fig_dir / f"{name}.png" if ok else None

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

    # ---- Q2 numbers ------------------------------------------------------------------------
    q2 = {}
    for lang in LANGS:
        cands = [(res.val("sort", lang, a, "random", big)[0], a) for a in SORT_ALGOS
                 if res.val("sort", lang, a, "random", big)[1]]
        t_lin, m_lin = res.val("search", lang, "Linear", "keyset", big)
        t_bin, m_bin = res.val("search", lang, "Binary", "keyset", big)
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
        ax.set_xscale("log")
        ax.set_yscale("log")
        _style(ax, "k (número de búsquedas)", "Tiempo total (s)", f"Ordenar o no ordenar (n = {thousands(big)})")
        ax.legend(fontsize=7.5)
        fig_q.tight_layout()
        fig_q.savefig(fig_dir / "p3_q2.png", dpi=170)
        plt.close(fig_q)
        figs["p3_q2"] = fig_dir / "p3_q2.png"

    # ---- PDF -------------------------------------------------------------------------------
    d = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    for name, f in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"),
                    ("DV-I", "DejaVuSans-Oblique.ttf"), ("DV-BI", "DejaVuSans-BoldOblique.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(d / f)))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")
    styles = {
        "body": ParagraphStyle("body", fontName="DV", fontSize=9, leading=12.5, alignment=TA_JUSTIFY, spaceAfter=5),
        "pending": ParagraphStyle("pending", fontName="DV-B", fontSize=9, leading=12.5, textColor=colors.red,
                                  spaceAfter=5),
        "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=14, leading=18, spaceBefore=10, spaceAfter=6,
                             keepWithNext=1),
        "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=11, leading=14, spaceBefore=8, spaceAfter=4,
                             keepWithNext=1),
        "cap": ParagraphStyle("cap", fontName="DV-I", fontSize=8, leading=10, alignment=TA_CENTER, spaceAfter=8),
        "title": ParagraphStyle("title", fontName="DV-B", fontSize=20, leading=26, alignment=TA_CENTER, spaceAfter=10),
        "sub": ParagraphStyle("sub", fontName="DV", fontSize=11, leading=15, alignment=TA_CENTER),
    }
    W = 17 * cm
    story = []

    def P(text, style="body"):
        story.append(Paragraph(text, styles[style]))

    def add_fig(key, caption, width=15.5 * cm):
        path = figs.get(key)
        if not path or not Path(path).exists():
            story.append(Paragraph(f"PENDIENTE: gráfica {key} sin datos.", styles["pending"]))
            return
        iw, ih = ImageReader(str(path)).getSize()
        story.append(KeepTogether([Image(str(path), width=width, height=width * ih / iw),
                                   Paragraph(caption, styles["cap"])]))

    def add_analysis(key):
        story.extend(narrative(ana_dir / f"{key}.md", styles))

    # Cover
    story.append(Spacer(1, 4 * cm))
    P(html.escape(meta["title"]), "title")
    P("Comparación experimental de algoritmos de ordenamiento y búsqueda", "sub")
    story.append(Spacer(1, 1 * cm))
    if meta.get("course"):
        P(html.escape(meta["course"]), "sub")
    for m in meta.get("members") or ["(Integrantes: completar en report/meta.json)"]:
        P(html.escape(m), "sub")
    if meta.get("repo_url"):
        P("Repositorio: " + html.escape(meta["repo_url"]), "sub")
    if meta.get("date"):
        P(html.escape(meta["date"]), "sub")
    story.append(PageBreak())

    # Methodology
    P("1. Metodología y condiciones del experimento", "h1")
    env = environment()
    P("<b>Implementación.</b> Cada algoritmo se implementó en dos lenguajes con la misma lógica: "
      f"Java (compilado, con JIT; {html.escape(env['Java'])}) y Python (interpretado; versión {env['Python']}). "
      "Las implementaciones se adaptaron de GeeksforGeeks (fuente principal, ver Tabla 1). Los ordenamientos "
      "trabajan en sitio sobre el arreglo recibido; las búsquedas devuelven un índice o -1.")
    P("<b>Datos.</b> Se generaron una sola vez con una semilla fija (tools/generate_data.py) y se guardaron en "
      "archivos de texto plano: arreglos de 1.000, 10.000, 100.000 y 1.000.000 enteros aleatorios de 8 dígitos "
      "(entre 10.000.000 y 99.999.999), junto con sus versiones ascendente y descendente y un archivo de 1.000 "
      "claves de búsqueda por tamaño (500 presentes y 500 ausentes). Todos los programas leen esos archivos, "
      "por lo que todos los algoritmos se evalúan con el mismo conjunto de datos.")
    P("<b>Medición.</b> Se mide únicamente la ejecución del algoritmo (la lectura de archivos y la copia del "
      "arreglo quedan fuera del tiempo) con System.nanoTime() en Java y time.perf_counter_ns() en Python. Cada "
      "medición se repite 5 veces sobre una copia nueva del arreglo; se reporta el promedio y la desviación "
      "estándar muestral. En Java se ejecuta antes un calentamiento (10 ejecuciones sobre 10.000 elementos por "
      "algoritmo de ordenamiento y 300 pasadas del conjunto de claves por algoritmo de búsqueda) que no entra "
      "en el promedio. Tras cada ejecución, y fuera del tiempo medido, se verifica que el arreglo quedó ordenado "
      "(y con la misma suma) o que cada búsqueda devolvió el resultado correcto.")
    P("<b>Valores estimados y fallos.</b> Antes de ejecutar un tamaño n, el programa estima su tiempo escalando el "
      "último promedio medido, t(n) = t(n<sub>prev</sub>) · f(n) / f(n<sub>prev</sub>), donde f es la "
      "complejidad teórica del algoritmo para esa entrada. Si la estimación supera 300 s por ejecución, no se "
      "ejecuta y el valor se marca como estimado. Si un algoritmo falla (desbordamiento de pila o límite de "
      "recursión), el error queda registrado en el CSV y en la Tabla A.3, y los tamaños mayores se estiman con "
      "el mismo escalamiento. En las gráficas los valores estimados se dibujan con línea punteada y marcador "
      "hueco (líneas) o barra rayada con prefijo «~» (barras); en las tablas llevan «~» y «(est.)».")
    P("<b>Entorno de pruebas.</b> " + html.escape("; ".join(f"{k}: {v}" for k, v in env.items())) + ".")
    P("<b>Tabla 1.</b> Fuentes (GeeksforGeeks) usadas para cada algoritmo.")
    story.append(make_table([["Algoritmo", "Fuente"]] + [[a, GFG + u] for a, u in SOURCES],
                            [5 * cm, 12 * cm], styles))

    # Point 1
    story.append(PageBreak())
    P("2. Punto 1 - Algoritmos de ordenamiento", "h1")
    P("<b>Tabla 2.</b> Complejidad teórica, estabilidad y uso de memoria (n elementos, d = 8 dígitos, b = 10 "
      "(base), k = número de cubetas).")
    story.append(make_table([
        ["Algoritmo", "Mejor caso", "Caso promedio", "Peor caso", "Estable", "In-place"],
        ["Insertion Sort", "O(n)", "O(n²)", "O(n²)", "Sí", "Sí"],
        ["Dual-Pivot QuickSort", "O(n log n)", "O(n log n)", "O(n²)", "No", "Sí (pila O(log n) en promedio)"],
        ["Merge Sort", "O(n log n)", "O(n log n)", "O(n log n)", "Sí", "No (O(n) auxiliar)"],
        ["Heap Sort", "O(n log n)", "O(n log n)", "O(n log n)", "No", "Sí"],
        ["Radix Sort (LSD, base 10)", "O(d·(n+b))", "O(d·(n+b))", "O(d·(n+b))", "Sí", "No (O(n+b) auxiliar)"],
        ["Bucket Sort", "O(n+k)", "O(n+k)", "O(n²)", "Sí (con inserción estable)", "No (O(n+k) auxiliar)"],
    ], [3.6 * cm, 2.4 * cm, 2.6 * cm, 2.4 * cm, 3 * cm, 3 * cm], styles))
    story.append(Spacer(1, 6))
    P("<b>Bucket Sort.</b> Se usan k = n cubetas de igual ancho sobre [mín, máx] del arreglo. El valor v se asigna "
      "a la cubeta ⌊(v − mín) · k / (máx − mín + 1)⌋. Las cubetas se almacenan de forma contigua (conteo y suma "
      "prefija) en lugar de una lista por cubeta, y cada cubeta se ordena con Insertion Sort, como en GeeksforGeeks.")
    P("<b>Dual-Pivot QuickSort.</b> Los pivotes son el primer y el último elemento (si el primero es mayor se "
      "intercambian). Con una entrada ya ordenada el pivote izquierdo es el mínimo y el derecho el máximo, por lo "
      "que cada llamada solo descarta 2 elementos: la recursión llega a profundidad ≈ n/2.")

    P("2.1 Crecimiento", "h2")
    for lang in LANGS:
        add_fig(f"p1_growth_{lang.lower()}", f"Figura 1{'a' if lang == 'Java' else 'b'}. Tiempo vs n ({lang}), "
                                              "entrada aleatoria, escala log-log.")
    P("<b>Tabla 3.</b> Factor de crecimiento del tiempo medio al multiplicar n por 10 (entrada aleatoria) frente al "
      "factor que predice la complejidad teórica. «~» indica que alguno de los extremos es estimado.")
    for lang in LANGS:
        rows = [[lang] + [f"{thousands(a)} → {thousands(b)}" for a, b in zip(sizes, sizes[1:])]]
        for alg in SORT_ALGOS:
            row = [SORT_LABEL[alg]]
            cost = sort_model(alg, "random")
            for a, b in zip(sizes, sizes[1:]):
                (va, ma), (vb, mb) = res.val("sort", lang, alg, "random", a), res.val("sort", lang, alg, "random", b)
                if va == va and vb == vb and va > 0:
                    mark = "" if (ma and mb) else "~"
                    row.append(f"{mark}×{vb / va:.1f} (teór. ×{cost(b) / cost(a):.1f})")
                else:
                    row.append("n/d")
            rows.append(row)
        first = 3.6 * cm
        other = (W - first) / max(1, len(sizes) - 1)
        story.append(make_table(rows, [first] + [other] * (len(sizes) - 1), styles))
        story.append(Spacer(1, 6))
    add_analysis("p1_growth")

    P("2.2 Efecto del orden de entrada (lenguaje compilado: Java)", "h2")
    for n_ in [x for x in (1_000, 10_000, 100_000) if x in sizes]:
        add_fig(f"p1_order_{n_}", f"Figura 2 (n = {thousands(n_)}). Tiempo por tipo de entrada, Java.")
    add_analysis("p1_order")

    P("2.3 Compilado frente a interpretado", "h2")
    add_fig("p1_compiled", f"Figura 3. Java vs Python, n = {thousands(big)}, entrada aleatoria.")
    add_analysis("p1_compiled")

    # Point 2
    story.append(PageBreak())
    P("3. Punto 2 - Algoritmos de búsqueda", "h1")
    P("<b>Tabla 4.</b> Complejidad teórica (sobre un arreglo ordenado de n elementos).")
    story.append(make_table([
        ["Algoritmo", "Mejor caso", "Peor caso / promedio", "Supuesto"],
        ["Lineal", "O(1)", "O(n)", "Ninguno (no requiere orden)"],
        ["Binaria", "O(1)", "O(log₂ n)", "Arreglo ordenado"],
        ["Ternaria", "O(1)", "O(log₃ n) iteraciones (≈2 comparaciones por iteración)", "Arreglo ordenado"],
        ["Por saltos", "O(1)", "O(√n)", "Arreglo ordenado"],
        ["Interpolación", "O(1)", "Promedio O(log log n) con datos uniformes; peor caso O(n)", "Ordenado y distribuido uniformemente"],
        ["Exponencial", "O(1)", "O(log i), i = posición de la clave", "Arreglo ordenado"],
    ], [2.8 * cm, 2 * cm, 8 * cm, 4.2 * cm], styles))
    story.append(Spacer(1, 6))
    P("Los arreglos de entrada son los ordenados ascendentemente del Punto 1. Cada medición busca el conjunto de "
      "1.000 claves (500 presentes y 500 ausentes), mide el tiempo total y reporta el promedio por búsqueda. Para "
      "la posición de la clave, se repite 1.000 veces la búsqueda de una clave ubicada al inicio, al centro y al "
      f"final del arreglo de n = {thousands(big)}.")
    P("3.1 Crecimiento", "h2")
    for lang in LANGS:
        add_fig(f"p2_growth_{lang.lower()}", f"Figura 4{'a' if lang == 'Java' else 'b'}. Tiempo promedio por "
                                              f"búsqueda vs n ({lang}), escala log-log.")
    add_analysis("p2_growth")
    P("3.2 Compilado frente a interpretado", "h2")
    add_fig("p2_compiled", f"Figura 5. Java vs Python, n = {thousands(big)}.")
    add_analysis("p2_compiled")
    P("3.3 Posición de la clave", "h2")
    for lang in LANGS:
        rows = [[f"{lang} (n = {thousands(big)})"] + [POS_LABEL[p] for p in POS_LABEL]]
        for alg in SEARCH_ALGOS:
            row = [SEARCH_LABEL[alg]]
            for scen in POS_LABEL:
                r = res.get("search", lang, alg, scen, big)
                row.append(fmt_pm(r["mean_s"], r["std_s"], r["measured"]) if r else "n/d")
            rows.append(row)
        P(f"<b>Tabla 5 ({lang}).</b> Tiempo promedio por búsqueda según la posición de la clave.")
        story.append(make_table(rows, [4 * cm, 4.3 * cm, 4.3 * cm, 4.4 * cm], styles))
        story.append(Spacer(1, 6))
    add_analysis("p2_position")

    # Point 3
    story.append(PageBreak())
    P("4. Punto 3 - Análisis comparativo", "h1")
    P("4.1 Comparativos frente a no comparativos", "h2")
    P(f"<b>Tabla 6.</b> Tiempos con n = {thousands(big)} (entrada aleatoria).")
    rows = [["Algoritmo", "Tipo", "Java", "Python"]]
    for alg in SORT_ALGOS:
        kind_ = "No comparativo" if alg in ("RadixSort", "BucketSort") else "Comparativo"
        rows.append([SORT_LABEL[alg], kind_] + [fmt_pm(*(lambda r: (r["mean_s"], r["std_s"], r["measured"]) if r
                                                        else (NAN, NAN, False))(res.get("sort", lg, alg, "random", big)))
                                                for lg in LANGS])
    story.append(make_table(rows, [4 * cm, 3 * cm, 5 * cm, 5 * cm], styles))
    story.append(Spacer(1, 6))
    add_analysis("p3_q1")
    P("4.2 ¿Ordenar o no ordenar?", "h2")
    P("Con k búsquedas sobre un arreglo desordenado de n elementos: (A) k búsquedas lineales cuestan "
      "k · t<sub>lineal</sub>; (B) ordenar una vez y luego k búsquedas binarias cuestan "
      "T<sub>orden</sub> + k · t<sub>binaria</sub>. Ordenar conviene cuando T<sub>orden</sub> + k·t<sub>binaria</sub> "
      "&lt; k·t<sub>lineal</sub>, es decir, k &gt; k* = T<sub>orden</sub> / (t<sub>lineal</sub> − "
      "t<sub>binaria</sub>). La búsqueda lineal de las 1.000 claves recorre el mismo número de elementos en un "
      "arreglo ordenado que en uno desordenado (no aprovecha el orden), por lo que se usa ese tiempo medido "
      "como t<sub>lineal</sub>.")
    if q2:
        rows = [["Lenguaje", "Mejor ordenamiento (medido)", "T_orden", "t_lineal", "t_binaria", "k*"]]
        for lang, v in q2.items():
            rows.append([lang, SORT_LABEL[v["alg"]], fmt_time(v["t_sort"]), fmt_time(v["t_lin"]),
                         fmt_time(v["t_bin"]), f"{v['k_star']:.1f} → {math.ceil(v['k_star'])} búsquedas"])
        P(f"<b>Tabla 7.</b> Cálculo del umbral k* con n = {thousands(big)}.")
        story.append(make_table(rows, [2 * cm, 4 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm, 3.2 * cm], styles))
        story.append(Spacer(1, 6))
        for lang, v in q2.items():
            P(f"<b>{lang}:</b> k* = {fmt_time(v['t_sort'])} / ({fmt_time(v['t_lin'])} − {fmt_time(v['t_bin'])}) "
              f"= {v['k_star']:.2f} ⇒ a partir de k = {math.ceil(v['k_star'])} búsquedas conviene ordenar.")
        add_fig("p3_q2", "Figura 6. Costo total de cada estrategia según k (las líneas punteadas verticales marcan k*).")
    else:
        P("PENDIENTE: faltan mediciones medidas (no estimadas) de ordenamiento y búsqueda para calcular k*.", "pending")
    add_analysis("p3_q2")

    # AI use
    P("5. Uso de inteligencia artificial", "h1")
    add_analysis("ai_use")
    P("6. Conclusiones", "h1")
    add_analysis("conclusions")

    # Appendix
    story.append(PageBreak())
    P("Anexo A. Tablas completas de resultados", "h1")
    P("Promedio ± desviación estándar muestral de 5 repeticiones. «~ … (est.)» = valor estimado, no medido.")
    for lang in LANGS:
        for v in ("random", "asc", "desc"):
            P(f"<b>Tabla A.1 - Ordenamiento, {lang}, entrada {VARIANT_LABEL[v].lower()}.</b>")
            story.append(results_table(res, "sort", lang, SORT_ALGOS, SORT_LABEL, v, sizes, styles))
            story.append(Spacer(1, 6))
    for lang in LANGS:
        P(f"<b>Tabla A.2 - Búsqueda, {lang}, tiempo por búsqueda (1.000 claves).</b>")
        story.append(results_table(res, "search", lang, SEARCH_ALGOS, SEARCH_LABEL, "keyset", sizes, styles))
        story.append(Spacer(1, 6))
    P("<b>Tabla A.3 - Registro de valores estimados y fallos.</b>")
    rows = [["Lenguaje", "Algoritmo", "Escenario", "n", "Estado", "Nota"]]
    for r in sorted(res.all_rows(), key=lambda r: (r["language"], r["algorithm"], r.get("variant") or r.get("scenario"), r["n"])):
        if not r["measured"] or r["status"] != "OK":
            rows.append([r["language"], r["algorithm"], r.get("variant") or r.get("scenario"), thousands(r["n"]),
                         r["status"], r["note"]])
    if len(rows) == 1:
        rows.append(["-", "-", "-", "-", "-", "Todas las ejecuciones se midieron sin errores."])
    story.append(make_table(rows, [1.6 * cm, 3.2 * cm, 1.8 * cm, 1.8 * cm, 3.1 * cm, 5.5 * cm], styles, font=6.5))
    story.append(Spacer(1, 8))
    P("<b>Reproducción.</b> Código fuente, datos (o el programa que los genera con semilla fija) y archivos de "
      "resultados: " + html.escape(meta.get("repo_url") or "(URL del repositorio: completar en report/meta.json)") + ".")

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("DV", 8)
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"{meta['title']}  -  página {doc_.page}")
        canvas.restoreState()

    pdf_path = out_dir / "Taller3.pdf"
    SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                      bottomMargin=2 * cm, title=meta["title"]).build(story, onFirstPage=footer, onLaterPages=footer)
    pending = [p.name for p in sorted(ana_dir.glob("*.md")) if p.read_text(encoding="utf-8").strip().upper().startswith("PENDIENTE")]
    print(f"PDF written: {pdf_path}")
    if pending:
        print("Sections still PENDIENTE (shown in red in the PDF): " + ", ".join(pending))


if __name__ == "__main__":
    main()
