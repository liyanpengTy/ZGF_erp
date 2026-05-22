"""轻量级本地 TTL 缓存工具。"""

from __future__ import annotations

import threading
import time


class SimpleTTLCache:
    """提供线程安全的本地 TTL 缓存，适合保存短周期的只读派生数据。"""

    def __init__(self, default_ttl=300):
        self.default_ttl = default_ttl
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        """读取缓存值；已过期或不存在时返回 ``None``。"""
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expire_at, value = item
            if expire_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key, value, ttl=None):
        """写入缓存值；未显式指定 TTL 时使用默认有效期。"""
        expire_at = time.time() + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self._store[key] = (expire_at, value)
        return value

    def delete(self, key):
        """删除单个缓存项。"""
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        """清空全部缓存项。"""
        with self._lock:
            self._store.clear()
