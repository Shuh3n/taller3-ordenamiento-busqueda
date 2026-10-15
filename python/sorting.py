"""Sorting algorithms adapted from GeeksforGeeks (URLs in README.md).

Every function sorts the list IN PLACE, ascending. The Java version (java/src/SortAlgorithms.java)
follows exactly the same logic.
"""


# --- Insertion Sort: https://www.geeksforgeeks.org/insertion-sort-algorithm/ ---------------------
def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key


# --- Dual-Pivot QuickSort (pivots = first and last element): GfG "dual-pivot-quicksort" ----------
def _partition(arr, low, high):
    if arr[low] > arr[high]:
        arr[low], arr[high] = arr[high], arr[low]
    j = k = low + 1
    g = high - 1
    p = arr[low]
    q = arr[high]
    while k <= g:
        if arr[k] < p:
            arr[k], arr[j] = arr[j], arr[k]
            j += 1
        elif arr[k] >= q:
            while arr[g] > q and k < g:
                g -= 1
            arr[k], arr[g] = arr[g], arr[k]
            g -= 1
            if arr[k] < p:
                arr[k], arr[j] = arr[j], arr[k]
                j += 1
        k += 1
    j -= 1
    g += 1
    arr[low], arr[j] = arr[j], arr[low]
    arr[high], arr[g] = arr[g], arr[high]
    return j, g


def _dual_pivot(arr, low, high):
    if low < high:
        lp, rp = _partition(arr, low, high)
        _dual_pivot(arr, low, lp - 1)
        _dual_pivot(arr, lp + 1, rp - 1)
        _dual_pivot(arr, rp + 1, high)


def dual_pivot_quick_sort(arr):
    _dual_pivot(arr, 0, len(arr) - 1)


# --- Merge Sort: https://www.geeksforgeeks.org/merge-sort/ ----------------------------------------
def _merge(arr, l, m, r):
    left = arr[l:m + 1]
    right = arr[m + 1:r + 1]
    n1, n2 = len(left), len(right)
    i = j = 0
    k = l
    while i < n1 and j < n2:
        if left[i] <= right[j]:
            arr[k] = left[i]
            i += 1
        else:
            arr[k] = right[j]
            j += 1
        k += 1
    while i < n1:
        arr[k] = left[i]
        i += 1
        k += 1
    while j < n2:
        arr[k] = right[j]
        j += 1
        k += 1


def _merge_sort(arr, l, r):
    if l < r:
        m = l + (r - l) // 2
        _merge_sort(arr, l, m)
        _merge_sort(arr, m + 1, r)
        _merge(arr, l, m, r)


def merge_sort(arr):
    _merge_sort(arr, 0, len(arr) - 1)


# --- Heap Sort: https://www.geeksforgeeks.org/heap-sort/ ------------------------------------------
def _heapify(arr, n, i):
    largest = i
    l = 2 * i + 1
    r = 2 * i + 2
    if l < n and arr[l] > arr[largest]:
        largest = l
    if r < n and arr[r] > arr[largest]:
        largest = r
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        _heapify(arr, n, largest)


def heap_sort(arr):
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        _heapify(arr, n, i)
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        _heapify(arr, i, 0)


# --- Radix Sort (LSD, base 10): https://www.geeksforgeeks.org/radix-sort/ -------------------------
def _counting_sort_by_digit(arr, exp):
    n = len(arr)
    output = [0] * n
    count = [0] * 10
    for v in arr:
        count[(v // exp) % 10] += 1
    for i in range(1, 10):
        count[i] += count[i - 1]
    for i in range(n - 1, -1, -1):
        d = (arr[i] // exp) % 10
        count[d] -= 1
        output[count[d]] = arr[i]
    arr[:] = output


def radix_sort(arr):
    if not arr:
        return
    m = max(arr)
    exp = 1
    while m // exp > 0:
        _counting_sort_by_digit(arr, exp)
        exp *= 10


# --- Bucket Sort: https://www.geeksforgeeks.org/bucket-sort-2/ -------------------------------------
# Adaptation for integers: k = n buckets of equal width over [min, max]. Value v goes to bucket
# floor((v - min) * k / (max - min + 1)). Buckets are laid out contiguously (count + prefix sum)
# instead of one list per bucket, and each bucket is sorted with insertion sort (as in GfG).
def bucket_sort(arr):
    n = len(arr)
    if n < 2:
        return
    lo, hi = min(arr), max(arr)
    if lo == hi:
        return
    k = n
    span = hi - lo + 1
    start = [0] * (k + 1)
    bucket_of = [0] * n
    for i in range(n):
        b = (arr[i] - lo) * k // span
        bucket_of[i] = b
        start[b + 1] += 1
    for b in range(k):
        start[b + 1] += start[b]
    nxt = start[:k]
    out = [0] * n
    for i in range(n):
        b = bucket_of[i]
        out[nxt[b]] = arr[i]
        nxt[b] += 1
    for b in range(k):
        s, e = start[b], start[b + 1]
        for i in range(s + 1, e):
            key = out[i]
            j = i - 1
            while j >= s and out[j] > key:
                out[j + 1] = out[j]
                j -= 1
            out[j + 1] = key
    arr[:] = out
