"""Custom hash map with separate chaining.

The restocking engine loads products into this map and retrieves them by
product id. Average insert, lookup, and delete are O(1). A chain of
colliding keys is O(k) for that bucket, and O(n) if every key collides.

Space complexity: O(n) entries plus O(capacity) buckets.

The database stays the source of truth. This structure is rebuilt from
query results whenever recommendations are calculated.

Collision handling: separate chaining. Each bucket is a list of
(key, value) pairs. The hash is a polynomial rolling hash so the
demonstration does not depend on Python's built-in dict.
"""


class InventoryHashMap:
    def __init__(self, capacity=64):
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._capacity = int(capacity)
        self._buckets = [[] for _ in range(self._capacity)]
        self._size = 0

    def _index(self, key):
        # 131 is a common polynomial base. Modulo keeps the index in range.
        digest = 0
        for character in str(key):
            digest = (digest * 131 + ord(character)) % self._capacity
        return digest

    def insert(self, key, value):
        """Insert or replace. Triggers a resize above a 0.75 load factor."""
        added = self._put(key, value)
        if added:
            self._size += 1
        if self._size > self._capacity * 0.75:
            self._resize()
        return self

    def _put(self, key, value):
        bucket = self._buckets[self._index(key)]
        for index, (existing, _value) in enumerate(bucket):
            if existing == key:
                bucket[index] = (key, value)
                return False
        bucket.append((key, value))
        return True

    def get(self, key, default=None):
        for existing, value in self._buckets[self._index(key)]:
            if existing == key:
                return value
        return default

    def delete(self, key):
        bucket = self._buckets[self._index(key)]
        for index, (existing, _value) in enumerate(bucket):
            if existing == key:
                bucket.pop(index)
                self._size -= 1
                return True
        return False

    def __contains__(self, key):
        return self.get(key, _MISSING) is not _MISSING

    def __getitem__(self, key):
        value = self.get(key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        self.insert(key, value)

    def __len__(self):
        return self._size

    def items(self):
        for bucket in self._buckets:
            for pair in bucket:
                yield pair

    def keys(self):
        for key, _value in self.items():
            yield key

    def _resize(self):
        previous = list(self.items())
        self._capacity *= 2
        self._buckets = [[] for _ in range(self._capacity)]
        self._size = 0
        for key, value in previous:
            self._put(key, value)
            self._size += 1


class _Missing:
    pass


_MISSING = _Missing()
