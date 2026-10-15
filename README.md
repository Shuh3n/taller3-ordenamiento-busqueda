# Workshop 3: Sorting and Searching Benchmarks

## Guía de pasos para el equipo (Taller 3: Ordenamiento y Búsqueda)

El taller compara 6 algoritmos de ordenamiento y 6 de búsqueda (12 en total), cada uno en **Java** (compilado)
y **Python** (interpretado): 24 implementaciones. Fuente principal: GeeksforGeeks.

### 1. Preparar el computador (cada integrante, una sola vez)

1. Instalar **JDK 17 o superior** (`javac -version` debe funcionar) y **Python 3.10 o superior**.
2. Instalar las librerías: `pip install numpy matplotlib reportlab`
3. Clonar el repositorio: `git clone <URL-del-repositorio>` y entrar a la carpeta del proyecto.

### 2. Ejecutar los experimentos (UNA sola persona, en UN solo computador)

Todas las mediciones deben salir de la misma máquina para que los tiempos sean comparables.

1. Prueba corta (unos minutos, no toca `results/`): `python run_all.py --quick`
2. Corrida completa (puede tardar de 1 a 2 horas): `python run_all.py`
   - Dejar el computador enchufado, sin programas pesados y sin ejecutar nada más en paralelo.
   - Si un paso falla, el script indica con qué comando continuar (`python run_all.py --steps ...`).
3. Al terminar quedan los CSV en `results/`, las gráficas en `report/figures/` y el PDF en `report/Taller3.pdf`.
4. Subir los resultados al repositorio: `git add results report && git commit -m "feat: add benchmark results" && git push`

### 3. Redactar el análisis (todo el equipo)

1. Cada integrante hace `git pull` y lee los resultados (`results/*.csv`, `report/figures/`).
2. El análisis vive en `report/analysis/*.md` (un archivo por sección). Los archivos que empiezan con
   `PENDIENTE` salen en rojo en el PDF. Repartan los archivos entre integrantes para evitar conflictos en git.
3. El texto debe ser **con sus propias palabras** y apoyarse en **sus mediciones** (tablas, gráficas o cálculos).
4. Completar `report/meta.json` (integrantes, curso, URL del repositorio) y revisar `report/analysis/ai_use.md`
   (sección «Uso de inteligencia artificial»: debe describir el uso real que hizo el grupo).
5. Regenerar el documento: `python tools/make_report.py` (usa los CSV ya existentes, no repite las mediciones).

### 4. Entrega

- **Un único PDF** (`report/Taller3.pdf`) con los tres puntos completos, subido por **una sola persona** en
  representación del grupo.
- El código, los resultados y los datos de prueba (o el programa que los genera con semilla fija,
  `tools/generate_data.py`) están en este repositorio.
- La sustentación es **grupal y obligatoria**: todos deben poder explicar el código y el análisis.

### Estructura del repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `run_all.py` | Ejecuta todo el flujo en orden (datos, compilación, 4 benchmarks, PDF) |
| `java/src/` | Algoritmos y benchmarks en Java |
| `python/` | Algoritmos y benchmarks en Python |
| `tools/` | Generador de datos (`generate_data.py`) y del PDF (`make_report.py`) |
| `results/` | CSV con todas las mediciones |
| `report/` | `meta.json`, `analysis/*.md`, `figures/` y `Taller3.pdf` |

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
report/                    meta.json, analysis/*.md (narrative), figures/ and Taller3.pdf (generated)
tools/make_report.py       figures + tables + final PDF from results/*.csv
```

## Requirements

JDK 17+ (tested with 26), Python 3.10+, and `pip install numpy matplotlib reportlab`.

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
5. Build figures and the PDF: `python tools/make_report.py` (writes `report/Taller3.pdf`)

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

`make_report.py` generates all figures and tables. The narrative lives in `report/analysis/*.md`; files that start
with `PENDIENTE` are rendered in red in the PDF. Edit `report/meta.json` with the group members and the repository URL.
