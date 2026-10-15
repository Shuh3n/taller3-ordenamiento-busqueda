"""Search algorithms adapted from GeeksforGeeks (URLs in README.md).

Every function takes a list sorted ascending and a key; it returns an index of the key or -1.
The Java version (java/src/SearchAlgorithms.java) follows exactly the same logic.
"""
import math


# --- Linear Search: https://www.geeksforgeeks.org/linear-search/ ----------------------------------
def linear_search(arr, x):
    for i in range(len(arr)):
        if arr[i] == x:
            return i
    return -1


# --- Binary Search (iterative): https://www.geeksforgeeks.org/binary-search/ ----------------------
def binary_search(arr, x):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if arr[mid] == x:
            return mid
        if arr[mid] < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


# --- Ternary Search (iterative): https://www.geeksforgeeks.org/ternary-search/ --------------------
def ternary_search(arr, x):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        third = (hi - lo) // 3
        m1 = lo + third
        m2 = hi - third
        if arr[m1] == x:
            return m1
        if arr[m2] == x:
            return m2
        if x < arr[m1]:
            hi = m1 - 1
        elif x > arr[m2]:
            lo = m2 + 1
        else:
            lo = m1 + 1
            hi = m2 - 1
    return -1


# --- Jump Search: https://www.geeksforgeeks.org/jump-search/ --------------------------------------
def jump_search(arr, x):
    n = len(arr)
    block = int(math.sqrt(n))
    step = block
    prev = 0
    while arr[min(step, n) - 1] < x:
        prev = step
        step += block
        if prev >= n:
            return -1
    while arr[prev] < x:
        prev += 1
        if prev == min(step, n):
            return -1
    return prev if arr[prev] == x else -1


# --- Interpolation Search: https://www.geeksforgeeks.org/interpolation-search/ --------------------
def interpolation_search(arr, x):
    lo, hi = 0, len(arr) - 1
    while lo <= hi and arr[lo] <= x <= arr[hi]:
        if arr[hi] == arr[lo]:
            return lo if arr[lo] == x else -1
        pos = lo + (hi - lo) * (x - arr[lo]) // (arr[hi] - arr[lo])
        if arr[pos] == x:
            return pos
        if arr[pos] < x:
            lo = pos + 1
        else:
            hi = pos - 1
    return -1


# --- Exponential Search: https://www.geeksforgeeks.org/exponential-search/ -----------------------
def _binary_range(arr, lo, hi, x):
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if arr[mid] == x:
            return mid
        if arr[mid] < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def exponential_search(arr, x):
    n = len(arr)
    if n == 0:
        return -1
    if arr[0] == x:
        return 0
    i = 1
    while i < n and arr[i] <= x:
        i *= 2
    return _binary_range(arr, i // 2, min(i, n - 1), x)
