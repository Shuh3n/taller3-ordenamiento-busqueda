import java.io.IOException;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.function.IntToDoubleFunction;

/** Shared helpers: argument parsing, data loading, statistics, CSV rows and cost models. */
final class Util {
    static final int[] SIZES = {1_000, 10_000, 100_000, 1_000_000};

    private Util() {}

    /** Parses "--key value" pairs. */
    static Map<String, String> parseArgs(String[] args) {
        Map<String, String> opts = new HashMap<>();
        for (int i = 0; i + 1 < args.length; i += 2) {
            opts.put(args[i].replaceFirst("^--", ""), args[i + 1]);
        }
        return opts;
    }

    static int[] loadInts(Path path) throws IOException {
        try (var lines = Files.lines(path)) {
            return lines.map(String::trim).filter(s -> !s.isEmpty()).mapToInt(Integer::parseInt).toArray();
        }
    }

    static long sum(int[] a) {
        long s = 0;
        for (int v : a) s += v;
        return s;
    }

    static boolean isSorted(int[] a) {
        for (int i = 0; i + 1 < a.length; i++) {
            if (a[i] > a[i + 1]) return false;
        }
        return true;
    }

    static double mean(double[] xs) {
        double s = 0;
        for (double x : xs) s += x;
        return s / xs.length;
    }

    /** Sample standard deviation (n-1). */
    static double std(double[] xs) {
        if (xs.length < 2) return 0.0;
        double m = mean(xs);
        double s = 0;
        for (double x : xs) s += (x - m) * (x - m);
        return Math.sqrt(s / (xs.length - 1));
    }

    static String num(double v) {
        return Double.isNaN(v) ? "" : Double.toString(v);
    }

    static void writeHeader(PrintWriter pw, String scenarioCol, int reps) {
        StringBuilder sb = new StringBuilder("language,algorithm," + scenarioCol + ",n");
        for (int r = 1; r <= reps; r++) sb.append(",rep").append(r);
        sb.append(",mean_s,std_s,measured,status,note");
        pw.println(sb);
        pw.flush();
    }

    /** Writes one CSV row. Notes must not contain commas. times == null for non-measured rows. */
    static void writeRow(PrintWriter pw, String algo, String scenario, int n, double[] times, int reps,
                         double mean, double std, boolean measured, String status, String note) {
        StringBuilder sb = new StringBuilder();
        sb.append("Java,").append(algo).append(',').append(scenario).append(',').append(n);
        for (int r = 0; r < reps; r++) {
            sb.append(',');
            if (times != null) sb.append(num(times[r]));
        }
        sb.append(',').append(num(mean)).append(',').append(measured ? num(std) : "");
        sb.append(',').append(measured).append(',').append(status).append(',').append(note);
        pw.println(sb);
        pw.flush();
    }

    // --- Theoretical cost models, used only to ESTIMATE runs that are not executed ---------------

    /** Scales the last measured mean from lastN to n; NaN when nothing was measured yet. */
    static double predict(double lastMean, int lastN, IntToDoubleFunction cost, int n) {
        if (Double.isNaN(lastMean)) return Double.NaN;
        return lastMean * cost.applyAsDouble(n) / cost.applyAsDouble(lastN);
    }

    private static double log2(double x) {
        return Math.log(x) / Math.log(2);
    }

    static IntToDoubleFunction sortModel(String algorithm, String variant) {
        switch (algorithm) {
            case "InsertionSort":
                if (variant.equals("asc")) return n -> n;
                return n -> (double) n * n;
            case "DualPivotQuickSort":
                if (variant.equals("random")) return n -> n * log2(n);
                return n -> (double) n * n;
            case "MergeSort":
            case "HeapSort":
                return n -> n * log2(n);
            default: // RadixSort (d = 8 digits) and BucketSort (uniform data)
                return n -> n;
        }
    }

    static IntToDoubleFunction searchModel(String algorithm) {
        switch (algorithm) {
            case "Linear":
                return n -> n;
            case "Jump":
                return n -> Math.sqrt(n);
            case "Interpolation":
                return n -> log2(log2(n));
            default: // Binary, Ternary, Exponential
                return n -> log2(n);
        }
    }
}
