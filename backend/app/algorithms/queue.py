"""Explicit FIFO queue for sequential inventory operations.

CSV imports and other batched stock updates are enqueued and then applied
one at a time, in submission order. A head index avoids O(n) pops from the
front of the list. The occasional compact is amortized O(1) per operation.

- enqueue: O(1) amortized
- dequeue: O(1) amortized
- peek:    O(1)
- is_empty: O(1)

Space complexity: O(n) for n waiting operations.

Python's collections.deque is the usual production queue. This class exists
so the academic demonstration shows the operations directly. The database
transaction around the whole batch is what keeps stock consistent; the queue
only controls order.
"""


class OperationQueue:
    def __init__(self):
        self._items = []
        self._head = 0

    def enqueue(self, item):
        self._items.append(item)

    def dequeue(self):
        if self.is_empty():
            raise IndexError("Cannot dequeue from an empty queue.")
        item = self._items[self._head]
        self._head += 1
        # Drop consumed prefix so a long import does not retain it forever.
        if self._head > 64 and self._head * 2 > len(self._items):
            self._items = self._items[self._head :]
            self._head = 0
        return item

    def peek(self):
        if self.is_empty():
            raise IndexError("Cannot peek an empty queue.")
        return self._items[self._head]

    def is_empty(self):
        return self._head >= len(self._items)

    def __len__(self):
        return len(self._items) - self._head
