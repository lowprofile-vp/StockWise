"""Binary min-heap used as a restocking priority queue.

The smallest priority is extracted first. Callers pass a numeric priority
where a lower value means a more urgent product (for example the negation
of the urgency score, then days until stockout).

Operations:
- insert:    O(log n)
- peek:      O(1)
- extract:   O(log n)
- heapify:   O(n)
- is_empty:  O(1)

Space complexity: O(n).

The heap stores (priority, sequence, item). The sequence is a tie break so
two equal priorities never compare the items themselves. That keeps the
heap usable when items are dictionaries.
"""


class PriorityQueue:
    def __init__(self):
        self._heap = []
        self._sequence = 0

    def insert(self, item, priority):
        self._sequence += 1
        self._heap.append(((priority, self._sequence), item))
        self._sift_up(len(self._heap) - 1)

    def peek(self):
        if self.is_empty():
            raise IndexError("Cannot peek an empty priority queue.")
        return self._heap[0][1]

    def extract(self):
        """Remove and return the most urgent item (lowest priority)."""
        if self.is_empty():
            raise IndexError("Cannot extract from an empty priority queue.")
        top = self._heap[0][1]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top

    def heapify(self, pairs):
        """Build a heap from (item, priority) pairs in O(n)."""
        self._heap = []
        for item, priority in pairs:
            self._sequence += 1
            self._heap.append(((priority, self._sequence), item))
        for index in range(len(self._heap) // 2 - 1, -1, -1):
            self._sift_down(index)

    def is_empty(self):
        return not self._heap

    def __len__(self):
        return len(self._heap)

    def _sift_up(self, index):
        heap = self._heap
        while index > 0:
            parent = (index - 1) // 2
            if heap[index][0] < heap[parent][0]:
                heap[index], heap[parent] = heap[parent], heap[index]
                index = parent
            else:
                return

    def _sift_down(self, index):
        heap = self._heap
        size = len(heap)
        while True:
            left = index * 2 + 1
            right = left + 1
            smallest = index
            if left < size and heap[left][0] < heap[smallest][0]:
                smallest = left
            if right < size and heap[right][0] < heap[smallest][0]:
                smallest = right
            if smallest == index:
                return
            heap[index], heap[smallest] = heap[smallest], heap[index]
            index = smallest
