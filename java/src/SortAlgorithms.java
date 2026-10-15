import java.util.Arrays;

/**
 * Sorting algorithms adapted from GeeksforGeeks (URLs in README.md).
 * Every method sorts the array IN PLACE, ascending. python/sorting.py follows exactly the same logic.
 */
final class SortAlgorithms {
    private SortAlgorithms() {}

    // --- Insertion Sort: https://www.geeksforgeeks.org/insertion-sort-algorithm/ -----------------
    static void insertionSort(int[] arr) {
        for (int i = 1; i < arr.length; i++) {
            int key = arr[i];
            int j = i - 1;
            while (j >= 0 && arr[j] > key) {
                arr[j + 1] = arr[j];
                j--;
            }
            arr[j + 1] = key;
        }
    }

    // --- Dual-Pivot QuickSort (pivots = first and last element): GfG "dual-pivot-quicksort" ------
    private static void swap(int[] a, int i, int j) {
        int t = a[i];
        a[i] = a[j];
        a[j] = t;
    }

    private static int[] partition(int[] arr, int low, int high) {
        if (arr[low] > arr[high]) swap(arr, low, high);
        int j = low + 1;
        int k = low + 1;
        int g = high - 1;
        int p = arr[low];
        int q = arr[high];
        while (k <= g) {
            if (arr[k] < p) {
                swap(arr, k, j);
                j++;
            } else if (arr[k] >= q) {
                while (arr[g] > q && k < g) g--;
                swap(arr, k, g);
                g--;
                if (arr[k] < p) {
                    swap(arr, k, j);
                    j++;
                }
            }
            k++;
        }
        j--;
        g++;
        swap(arr, low, j);
        swap(arr, high, g);
        return new int[] {j, g};
    }

    private static void dualPivot(int[] arr, int low, int high) {
        if (low < high) {
            int[] piv = partition(arr, low, high);
            dualPivot(arr, low, piv[0] - 1);
            dualPivot(arr, piv[0] + 1, piv[1] - 1);
            dualPivot(arr, piv[1] + 1, high);
        }
    }

    static void dualPivotQuickSort(int[] arr) {
        dualPivot(arr, 0, arr.length - 1);
    }

    // --- Merge Sort: https://www.geeksforgeeks.org/merge-sort/ ------------------------------------
    private static void merge(int[] arr, int l, int m, int r) {
        int n1 = m - l + 1;
        int n2 = r - m;
        int[] left = new int[n1];
        int[] right = new int[n2];
        System.arraycopy(arr, l, left, 0, n1);
        System.arraycopy(arr, m + 1, right, 0, n2);
        int i = 0, j = 0, k = l;
        while (i < n1 && j < n2) {
            if (left[i] <= right[j]) arr[k++] = left[i++];
            else arr[k++] = right[j++];
        }
        while (i < n1) arr[k++] = left[i++];
        while (j < n2) arr[k++] = right[j++];
    }

    private static void mergeSort(int[] arr, int l, int r) {
        if (l < r) {
            int m = l + (r - l) / 2;
            mergeSort(arr, l, m);
            mergeSort(arr, m + 1, r);
            merge(arr, l, m, r);
        }
    }

    static void mergeSort(int[] arr) {
        mergeSort(arr, 0, arr.length - 1);
    }

    // --- Heap Sort: https://www.geeksforgeeks.org/heap-sort/ --------------------------------------
    private static void heapify(int[] arr, int n, int i) {
        int largest = i;
        int l = 2 * i + 1;
        int r = 2 * i + 2;
        if (l < n && arr[l] > arr[largest]) largest = l;
        if (r < n && arr[r] > arr[largest]) largest = r;
        if (largest != i) {
            swap(arr, i, largest);
            heapify(arr, n, largest);
        }
    }

    static void heapSort(int[] arr) {
        int n = arr.length;
        for (int i = n / 2 - 1; i >= 0; i--) heapify(arr, n, i);
        for (int i = n - 1; i > 0; i--) {
            swap(arr, 0, i);
            heapify(arr, i, 0);
        }
    }

    // --- Radix Sort (LSD, base 10): https://www.geeksforgeeks.org/radix-sort/ ---------------------
    private static void countingSortByDigit(int[] arr, long exp) {
        int n = arr.length;
        int[] output = new int[n];
        int[] count = new int[10];
        for (int v : arr) count[(int) ((v / exp) % 10)]++;
        for (int i = 1; i < 10; i++) count[i] += count[i - 1];
        for (int i = n - 1; i >= 0; i--) {
            int d = (int) ((arr[i] / exp) % 10);
            count[d]--;
            output[count[d]] = arr[i];
        }
        System.arraycopy(output, 0, arr, 0, n);
    }

    static void radixSort(int[] arr) {
        if (arr.length == 0) return;
        int max = arr[0];
        for (int v : arr) if (v > max) max = v;
        for (long exp = 1; max / exp > 0; exp *= 10) countingSortByDigit(arr, exp);
    }

    // --- Bucket Sort: https://www.geeksforgeeks.org/bucket-sort-2/ --------------------------------
    // Adaptation for integers: k = n buckets of equal width over [min, max]. Value v goes to bucket
    // floor((v - min) * k / (max - min + 1)). Buckets are laid out contiguously (count + prefix sum)
    // instead of one list per bucket, and each bucket is sorted with insertion sort (as in GfG).
    static void bucketSort(int[] arr) {
        int n = arr.length;
        if (n < 2) return;
        int min = arr[0], max = arr[0];
        for (int v : arr) {
            if (v < min) min = v;
            if (v > max) max = v;
        }
        if (min == max) return;
        int k = n;
        long span = (long) max - min + 1;
        int[] start = new int[k + 1];
        int[] bucketOf = new int[n];
        for (int i = 0; i < n; i++) {
            int b = (int) (((long) (arr[i] - min)) * k / span);
            bucketOf[i] = b;
            start[b + 1]++;
        }
        for (int b = 0; b < k; b++) start[b + 1] += start[b];
        int[] next = Arrays.copyOf(start, k);
        int[] out = new int[n];
        for (int i = 0; i < n; i++) out[next[bucketOf[i]]++] = arr[i];
        for (int b = 0; b < k; b++) {
            int s = start[b], e = start[b + 1];
            for (int i = s + 1; i < e; i++) {
                int key = out[i];
                int j = i - 1;
                while (j >= s && out[j] > key) {
                    out[j + 1] = out[j];
                    j--;
                }
                out[j + 1] = key;
            }
        }
        System.arraycopy(out, 0, arr, 0, n);
    }
}
