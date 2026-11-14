"""Comparison sorts used to rank products.

Both functions return a new list and do not modify the input.

Merge sort
- Time:  O(n log n) worst, average, and best case.
- Space: O(n) for the merged copies.
- Stable: equal keys keep their original relative order (`<=` prefers the left half).

Quick sort
- Time:  O(n log n) average, O(n^2) worst case.
- Space: O(log n) average recursion, O(n) worst-case recursion.
- Not stable.
- Pivot: median-of-three, which avoids the already-sorted worst case of a
  fixed end pivot. The worst case is still possible on adversarial input.

The inventory list uses merge sort for names and quick sort for numeric
columns. Greedy budget selection uses merge sort so equal cost ratios stay
in urgency order.
"""


def merge_sort(items, key=None):
    source = list(items)
    if key is None:
        key = lambda value: value
    return _merge_sort(source, key)


def _merge_sort(items, key):
    if len(items) <= 1:
        return items
    mid = len(items) // 2
    left = _merge_sort(items[:mid], key)
    right = _merge_sort(items[mid:], key)
    return _merge(left, right, key)


def _merge(left, right, key):
    merged = []
    i = 0
    j = 0
    while i < len(left) and j < len(right):
        # `<=` keeps the left item when keys tie, which makes the sort stable.
        if key(left[i]) <= key(right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def quick_sort(items, key=None):
    copied = list(items)
    if key is None:
        key = lambda value: value
    _quick_sort(copied, 0, len(copied) - 1, key)
    return copied


def _quick_sort(items, low, high, key):
    if low >= high:
        return
    pivot_index = _partition(items, low, high, key)
    _quick_sort(items, low, pivot_index - 1, key)
    _quick_sort(items, pivot_index + 1, high, key)


def _median_of_three(items, low, high, key):
    mid = (low + high) // 2
    low_key = key(items[low])
    mid_key = key(items[mid])
    high_key = key(items[high])
    if low_key <= mid_key <= high_key or high_key <= mid_key <= low_key:
        return mid
    if mid_key <= low_key <= high_key or high_key <= low_key <= mid_key:
        return low
    return high


def _partition(items, low, high, key):
    pivot_at = _median_of_three(items, low, high, key)
    items[pivot_at], items[high] = items[high], items[pivot_at]
    pivot = key(items[high])
    store = low
    for index in range(low, high):
        if key(items[index]) <= pivot:
            items[store], items[index] = items[index], items[store]
            store += 1
    items[store], items[high] = items[high], items[store]
    return store
