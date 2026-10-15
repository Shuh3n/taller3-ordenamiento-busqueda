import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.IntToDoubleFunction;

/**
 * Point 1 benchmark (Java). Usage:
 *   java -cp java/out BenchSort [--data data] [--out results/sort_java.csv]
 *                               [--max-n 1000000] [--reps 5] [--limit-seconds 300]
 */
public class BenchSort {
    interface Sorter {
        void sort(int[] a);
    }

    static final String[] VARIANTS = {"random", "asc", "desc"};

    public static void main(String[] args) throws Exception {
        Map<String, String> opt = Util.parseArgs(args);
        Path dataDir = Paths.get(opt.getOrDefault("data", "data"));
        Path outPath = Paths.get(opt.getOrDefault("out", "results/sort_java.csv"));
        int maxN = Integer.parseInt(opt.getOrDefault("max-n", "1000000"));
        int reps = Integer.parseInt(opt.getOrDefault("reps", "5"));
        double limit = Double.parseDouble(opt.getOrDefault("limit-seconds", "300"));
        int[] sizes = Arrays.stream(Util.SIZES).filter(n -> n <= maxN).toArray();

        // Data is read BEFORE any measurement; file I/O is never timed.
        Map<String, int[]> data = new HashMap<>();
        for (int n : sizes) {
            for (String v : VARIANTS) {
                data.put(v + "_" + n, Util.loadInts(dataDir.resolve(v + "_" + n + ".txt")));
            }
        }
        int[] warm = Util.loadInts(dataDir.resolve("random_10000.txt"));

        Map<String, Sorter> algos = new LinkedHashMap<>();
        algos.put("InsertionSort", SortAlgorithms::insertionSort);
        algos.put("DualPivotQuickSort", SortAlgorithms::dualPivotQuickSort);
        algos.put("MergeSort", SortAlgorithms::mergeSort);
        algos.put("HeapSort", SortAlgorithms::heapSort);
        algos.put("RadixSort", SortAlgorithms::radixSort);
        algos.put("BucketSort", SortAlgorithms::bucketSort);

        if (outPath.getParent() != null) Files.createDirectories(outPath.getParent());
        try (PrintWriter pw = new PrintWriter(Files.newBufferedWriter(outPath))) {
            Util.writeHeader(pw, "variant", reps);
            for (Map.Entry<String, Sorter> e : algos.entrySet()) {
                warmUp(e.getValue(), warm); // JIT warm-up, never part of the reported times
                for (String v : VARIANTS) {
                    runSeries(pw, e.getKey(), e.getValue(), v, sizes, data, reps, limit);
                }
            }
        }
        System.out.println("Done -> " + outPath);
    }

    static void warmUp(Sorter s, int[] warm) {
        for (int i = 0; i < 10; i++) {
            int[] a = warm.clone();
            s.sort(a);
        }
    }

    static void runSeries(PrintWriter pw, String algo, Sorter sorter, String variant, int[] sizes,
                          Map<String, int[]> data, int reps, double limit) {
        IntToDoubleFunction cost = Util.sortModel(algo, variant);
        double lastMean = Double.NaN;
        int lastN = 0;
        boolean failed = false;
        for (int n : sizes) {
            int[] base = data.get(variant + "_" + n);
            double est = Util.predict(lastMean, lastN, cost, n);
            if (failed) {
                Util.writeRow(pw, algo, variant, n, null, reps, est, Double.NaN, false, "ESTIMATED",
                        "same failure expected (recursion depth grows with n); scaled from n=" + lastN);
                continue;
            }
            if (est > limit) {
                Util.writeRow(pw, algo, variant, n, null, reps, est, Double.NaN, false, "ESTIMATED",
                        String.format("predicted %.0fs > limit %.0fs; scaled from n=%d", est, limit, lastN));
                continue;
            }
            try {
                double[] times = new double[reps];
                long expectedSum = Util.sum(base);
                boolean ok = true;
                for (int r = 0; r < reps; r++) {
                    int[] a = base.clone(); // fresh copy per repetition, not timed
                    System.gc();
                    long t0 = System.nanoTime();
                    sorter.sort(a);
                    long t1 = System.nanoTime();
                    times[r] = (t1 - t0) / 1e9;
                    ok &= Util.isSorted(a) && Util.sum(a) == expectedSum; // verification, not timed
                }
                double mean = Util.mean(times);
                Util.writeRow(pw, algo, variant, n, times, reps, mean, Util.std(times), true,
                        ok ? "OK" : "VERIFICATION_FAILED", "");
                lastMean = mean;
                lastN = n;
                System.out.printf("%-20s %-7s n=%-8d mean=%.6fs%n", algo, variant, n, mean);
            } catch (StackOverflowError so) {
                failed = true;
                Util.writeRow(pw, algo, variant, n, null, reps, est, Double.NaN, false, "ERROR_StackOverflowError",
                        "StackOverflowError at n=" + n + "; scaled from n=" + lastN);
                System.out.printf("%-20s %-7s n=%-8d StackOverflowError%n", algo, variant, n);
            }
        }
    }
}
