/**
 * Search algorithms adapted from GeeksforGeeks (URLs in README.md).
 * Every method takes an array sorted ascending and a key; it returns an index of the key or -1.
 * python/searching.py follows exactly the same logic.
 */
final class SearchAlgorithms {
    private SearchAlgorithms() {}

    // --- Linear Search: https://www.geeksforgeeks.org/linear-search/ ------------------------------
    static int linearSearch(int[] arr, int x) {
        for (int i = 0; i < arr.length; i++) {
            if (arr[i] == x) return i;
        }
        return -1;
    }

    // --- Binary Search (iterative): https://www.geeksforgeeks.org/binary-search/ -------------------
    static int binarySearch(int[] arr, int x) {
        int lo = 0, hi = arr.length - 1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (arr[mid] == x) return mid;
            if (arr[mid] < x) lo = mid + 1;
            else hi = mid - 1;
        }
        return -1;
    }

    // --- Ternary Search (iterative): https://www.geeksforgeeks.org/ternary-search/ -----------------
    static int ternarySearch(int[] arr, int x) {
        int lo = 0, hi = arr.length - 1;
        while (lo <= hi) {
            int third = (hi - lo) / 3;
            int m1 = lo + third;
            int m2 = hi - third;
            if (arr[m1] == x) return m1;
            if (arr[m2] == x) return m2;
            if (x < arr[m1]) {
                hi = m1 - 1;
            } else if (x > arr[m2]) {
                lo = m2 + 1;
            } else {
                lo = m1 + 1;
                hi = m2 - 1;
            }
        }
        return -1;
    }

    // --- Jump Search: https://www.geeksforgeeks.org/jump-search/ -----------------------------------
    static int jumpSearch(int[] arr, int x) {
        int n = arr.length;
        int block = (int) Math.sqrt(n);
        int step = block;
        int prev = 0;
        while (arr[Math.min(step, n) - 1] < x) {
            prev = step;
            step += block;
            if (prev >= n) return -1;
        }
        while (arr[prev] < x) {
            prev++;
            if (prev == Math.min(step, n)) return -1;
        }
        return arr[prev] == x ? prev : -1;
    }

    // --- Interpolation Search: https://www.geeksforgeeks.org/interpolation-search/ -----------------
    static int interpolationSearch(int[] arr, int x) {
        int lo = 0, hi = arr.length - 1;
        while (lo <= hi && x >= arr[lo] && x <= arr[hi]) {
            if (arr[hi] == arr[lo]) return arr[lo] == x ? lo : -1;
            int pos = lo + (int) (((long) (hi - lo) * (x - arr[lo])) / (arr[hi] - arr[lo]));
            if (arr[pos] == x) return pos;
            if (arr[pos] < x) lo = pos + 1;
            else hi = pos - 1;
        }
        return -1;
    }

    // --- Exponential Search: https://www.geeksforgeeks.org/exponential-search/ --------------------
    private static int binaryRange(int[] arr, int lo, int hi, int x) {
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (arr[mid] == x) return mid;
            if (arr[mid] < x) lo = mid + 1;
            else hi = mid - 1;
        }
        return -1;
    }

    static int exponentialSearch(int[] arr, int x) {
        int n = arr.length;
        if (n == 0) return -1;
        if (arr[0] == x) return 0;
        int i = 1;
        while (i < n && arr[i] <= x) i *= 2;
        return binaryRange(arr, i / 2, Math.min(i, n - 1), x);
    }
}
