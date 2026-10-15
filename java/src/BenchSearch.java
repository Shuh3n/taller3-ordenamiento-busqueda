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
 * Point 2 benchmark (Java). Usage:
 *   java -cp java/out BenchSearch [--data data] [--out results/search_java.csv]
 *                                 [--max-n 1000000] [--reps 5] [--limit-seconds 300]
 *
 * Scenarios: keyset (the 1,000 keys of keys_<n>.txt) at every n, and pos_start / pos_center /
 * pos_end (the same key searched 1,000 times) at the largest n only. Reported time = seconds per search.
 */
public class BenchSearch {
    interface Searcher {
        int search(int[] a, int x);
    }

    static final int POSITION_REPEATS = 1_000;

    public static void main(String[] args) throws Exception {
        Map<String, String> opt = Util.parseArgs(args);
        Path dataDir = Paths.get(opt.getOrDefault("data", "data"));
        Path outPath = Paths.get(opt.getOrDefault("out", "results/search_java.csv"));
        int maxN = Integer.parseInt(opt.getOrDefault("max-n", "1000000"));
        int reps = Integer.parseInt(opt.getOrDefault("reps", "5"));
        double limit = Double.parseDouble(opt.getOrDefault("limit-seconds", "300"));
        int[] sizes = Arrays.stream(Util.SIZES).filter(n -> n <= maxN).toArray();
        int positionN = sizes[sizes.length - 1];

        Map<Integer, int[]> arrays = new HashMap<>();
        Map<Integer, int[]> keys = new HashMap<>();
        for (int n : sizes) {
            arrays.put(n, Util.loadInts(dataDir.resolve("asc_" + n + ".txt")));
            keys.put(n, Util.loadInts(dataDir.resolve("keys_" + n + ".txt")));
        }
        int[] warmArr = Util.loadInts(dataDir.resolve("asc_10000.txt"));
        int[] warmKeys = Util.loadInts(dataDir.resolve("keys_10000.txt"));

        Map<String, Searcher> algos = new LinkedHashMap<>();
        algos.put("Linear", SearchAlgorithms::linearSearch);
        algos.put("Binary", SearchAlgorithms::binarySearch);
        algos.put("Ternary", SearchAlgorithms::ternarySearch);
        algos.put("Jump", SearchAlgorithms::jumpSearch);
        algos.put("Interpolation", SearchAlgorithms::interpolationSearch);
        algos.put("Exponential", SearchAlgorithms::exponentialSearch);

        if (outPath.getParent() != null) Files.createDirectories(outPath.getParent());
        try (PrintWriter pw = new PrintWriter(Files.newBufferedWriter(outPath))) {
            Util.writeHeader(pw, "scenario", reps);
            for (Map.Entry<String, Searcher> e : algos.entrySet()) {
                String algo = e.getKey();
                Searcher s = e.getValue();
                int[] res = new int[warmKeys.length];
                for (int i = 0; i < 300; i++) timeKeys(s, warmArr, warmKeys, res); // JIT warm-up, not reported
                IntToDoubleFunction cost = Util.searchModel(algo);

                // Scenario 1: key set, every n.
                double lastMean = Double.NaN;
                int lastN = 0;
                for (int n : sizes) {
                    double est = Util.predict(lastMean, lastN, cost, n);
                    if (est * keys.get(n).length > limit) { // predicted time of one full pass over the keys
                        Util.writeRow(pw, algo, "keyset", n, null, reps, est, Double.NaN, false, "ESTIMATED",
                                String.format("predicted > limit; scaled from n=%d", lastN));
                        continue;
                    }
                    double mean = runScenario(pw, algo, "keyset", s, arrays.get(n), keys.get(n), n, reps);
                    lastMean = mean;
                    lastN = n;
                }

                // Scenarios 2-4: key position, largest n only.
                int[] arr = arrays.get(positionN);
                int[] positions = {0, positionN / 2, positionN - 1};
                String[] names = {"pos_start", "pos_center", "pos_end"};
                for (int p = 0; p < 3; p++) {
                    int[] same = new int[POSITION_REPEATS];
                    Arrays.fill(same, arr[positions[p]]);
                    runScenario(pw, algo, names[p], s, arr, same, positionN, reps);
                }
            }
        }
        System.out.println("Done -> " + outPath);
    }

    /** Seconds per search for one pass over all keys. */
    static double timeKeys(Searcher s, int[] arr, int[] keys, int[] res) {
        long t0 = System.nanoTime();
        for (int i = 0; i < keys.length; i++) res[i] = s.search(arr, keys[i]);
        long t1 = System.nanoTime();
        return (t1 - t0) / 1e9 / keys.length;
    }

    static boolean verify(int[] arr, int[] keys, int[] res) {
        for (int i = 0; i < keys.length; i++) {
            boolean present = Arrays.binarySearch(arr, keys[i]) >= 0;
            if (present) {
                if (res[i] < 0 || arr[res[i]] != keys[i]) return false;
            } else if (res[i] != -1) {
                return false;
            }
        }
        return true;
    }

    static double runScenario(PrintWriter pw, String algo, String scenario, Searcher s, int[] arr, int[] keys,
                              int n, int reps) {
        double[] times = new double[reps];
        int[] res = new int[keys.length];
        boolean ok = true;
        for (int r = 0; r < reps; r++) {
            System.gc();
            times[r] = timeKeys(s, arr, keys, res);
            ok &= verify(arr, keys, res); // verification, not timed
        }
        double mean = Util.mean(times);
        Util.writeRow(pw, algo, scenario, n, times, reps, mean, Util.std(times), true,
                ok ? "OK" : "VERIFICATION_FAILED", "");
        System.out.printf("%-14s %-11s n=%-8d mean=%.3e s/search%n", algo, scenario, n, mean);
        return mean;
    }
}
