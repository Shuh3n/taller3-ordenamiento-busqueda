# Workshop 3: Sorting and Searching Benchmarks

## Guía de pasos para el equipo (Taller 3: Ordenamiento y Búsqueda)

El taller compara 6 algoritmos de ordenamiento y 6 de búsqueda (12 en total), cada uno en **Java** (compilado)
y **Python** (interpretado): 24 implementaciones. Fuente principal: GeeksforGeeks.

### 1. Preparar el computador (cada integrante, una sola vez)

1. Instalar **JDK 17 o superior** (`javac -version` debe funcionar) y **Python 3.10 o superior**.
2. Instalar las librerías: `pip install numpy matplotlib`
3. Clonar el repositorio: `git clone <URL-del-repositorio>` y entrar a la carpeta del proyecto.

### 2. Ejecutar los experimentos (UNA sola persona, en UN solo computador)

Todas las mediciones deben salir de la misma máquina para que los tiempos sean comparables.

1. Prueba corta (unos minutos, no toca `results/`): `python run_all.py --quick`
2. Corrida completa (puede tardar de 1 a 2 horas): `python run_all.py`
   - Dejar el computador enchufado, sin programas pesados y sin ejecutar nada más en paralelo.
   - Si un paso falla, el script indica con qué comando continuar (`python run_all.py --steps ...`).
3. Al terminar quedan los CSV en `results/` y las gráficas en `report/figures/` (solo resultados y gráficas).
4. Subir los resultados al repositorio: `git add results report && git commit -m "feat: add benchmark results" && git push`

### 3. Redactar el informe (todo el equipo)

1. Cada integrante hace `git pull` y lee los resultados (`results/*.csv` y `report/figures/*.png`).
2. El informe lo redacta **a mano** todo el equipo, apoyándose en esos CSV y gráficas.
   Este repositorio solo entrega resultados y gráficas: el documento final no sale del código.

### 4. Entrega

- El informe final, escrito a mano por el equipo con los CSV y las gráficas de este repositorio, lo sube
  **una sola persona** en representación del grupo.
- El código, los resultados y los datos de prueba (o el programa que los genera con semilla fija,
  `tools/generate_data.py`) están en este repositorio.
- La sustentación es **grupal y obligatoria**: todos deben poder explicar el código y el análisis.

### Estructura del repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `run_all.py` | Ejecuta todo el flujo en orden (datos, compilación, 4 benchmarks y gráficas) |
| `java/src/` | Algoritmos y benchmarks en Java |
| `python/` | Algoritmos y benchmarks en Python |
| `tools/` | Generador de datos (`generate_data.py`) y de gráficas (`make_figures.py`) |
| `results/` | CSV con todas las mediciones |
| `report/` | Gráficas (PNG) generadas a partir de los CSV |

---

## Technical reference

Experimental comparison of 6 sorting algorithms and 6 search algorithms, each implemented in
**Java** (compiled, JIT) and **Python** (interpreted) with identical logic. The main reference for every
implementation is GeeksforGeeks.

| Algorithm | Source |
|---|---|
| Insertion Sort | https://www.geeksforgeeks.org/insertion-sort-algorithm/ |
| Dual-Pivot QuickSort | https://www.geeksforgeeks.org/dual-pivot-quicksort/ |
| Merge Sort | https://www.geeksforgeeks.org/merge-sort/ |
| Heap Sort | https://www.geeksforgeeks.org/heap-sort/ |
| Radix Sort | https://www.geeksforgeeks.org/radix-sort/ |
| Bucket Sort | https://www.geeksforgeeks.org/bucket-sort-2/ |
| Linear / Binary / Ternary search | https://www.geeksforgeeks.org/linear-search/ , `binary-search/` , `ternary-search/` |
| Jump / Interpolation / Exponential search | https://www.geeksforgeeks.org/jump-search/ , `interpolation-search/` , `exponential-search/` |

## Layout

```
tools/generate_data.py     generates the test data (fixed seed, plain text)
java/src/                  SortAlgorithms, SearchAlgorithms, BenchSort, BenchSearch, Util
python/                    sorting.py, searching.py, bench_sort.py, bench_search.py, common.py
results/                   CSV output of the benchmarks (4 files)
report/figures/            PNG figures generated from results/*.csv
```

## Requirements

JDK 17+ (tested with 26), Python 3.10+, and `pip install numpy matplotlib`.

## How to run

**Everything at once:** `python run_all.py` (or `python run_all.py --quick` for a smoke test). It runs the steps
below sequentially and stops at the first failure. Manual steps, in order, one at a time:

1. Generate the data (once; ~30 MB, ignored by git, reproducible from seed 42):
   `python tools/generate_data.py`
2. Compile Java:
   `javac -d java/out java/src/Util.java java/src/SortAlgorithms.java java/src/SearchAlgorithms.java java/src/BenchSort.java java/src/BenchSearch.java`
3. Sorting benchmarks:
   `java -cp java/out BenchSort` and `python python/bench_sort.py`
4. Search benchmarks:
   `java -cp java/out BenchSearch` and `python python/bench_search.py`
5. Build the figures: `python tools/make_figures.py` (writes `report/figures/*.png`).

**Quick smoke test** (a couple of minutes): add `--max-n 10000 --reps 2 --out smoke/<file>.csv` to any
benchmark command, and do not use those files for the report.

**Measurement hygiene.** Run the benchmarks one after another, never in parallel, with the computer plugged in
and no heavy applications open; parallel runs compete for CPU and distort the times. The full run takes a while
(Java Insertion Sort at n = 1,000,000 and the pure-Python searches/sorts at n = 1,000,000 are the slowest parts).
Options of every benchmark: `--data`, `--out`, `--max-n`, `--reps` (default 5), `--limit-seconds` (default 300).

## Method

- **Data:** n = 1,000 / 10,000 / 100,000 / 1,000,000 random 8-digit integers (10,000,000 to 99,999,999) written to
  `data/random_<n>.txt`, plus `asc_<n>.txt`, `desc_<n>.txt` and `keys_<n>.txt` (500 present + 500 absent keys).
  Programs read these files before timing; file I/O is never measured.
- **Timing:** `System.nanoTime()` (Java) / `time.perf_counter_ns()` (Python); 5 repetitions on a fresh copy of the
  array, reporting mean and sample standard deviation. Java runs an untimed JIT warm-up first.
- **Verification:** after every run, outside the timed section, sortedness (+ checksum) or search correctness is checked.
- **Estimated values:** before running size n the program scales the last measured mean with the theoretical cost
  model (`t(n) = t(n_prev) * f(n) / f(n_prev)`); if the prediction exceeds the limit (300 s per execution) the run is
  skipped and recorded as estimated. A failing run (`StackOverflowError` in Java, `RecursionError` in Python) is recorded
  with its error status and larger sizes are estimated the same way.
- **Search timing:** the 1,000 keys are searched in one timed pass and the average per search is reported; key-position
  scenarios (`pos_start`, `pos_center`, `pos_end`) search the same key 1,000 times at the largest n.

## CSV format

`language, algorithm, variant|scenario, n, rep1..rep5, mean_s, std_s, measured, status, note`
(times in seconds; for search, seconds per search). `measured=false` rows are estimates; `status` is `OK`,
`ESTIMATED`, `ERROR_StackOverflowError`, `ERROR_RecursionError` or `VERIFICATION_FAILED`.

## Writing the report

`make_figures.py` generates all PNG figures from the CSV files in `results/`.
