import threading
import time
from collections import defaultdict, deque


class FailureLimiter:
    """Limita tentativas malsucedidas por chave em uma janela deslizante (em memória).

    Limitação conhecida: o estado vive no processo. Com vários workers/instâncias cada um
    conta separadamente; para produção em escala, use um armazenamento compartilhado (ex.: Redis)
    ou um limitador no proxy reverso/API gateway.
    """

    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._failures[key]
        while events and now - events[0] >= self.window_seconds:
            events.popleft()
        if not events:
            self._failures.pop(key, None)
        return events

    def retry_after(self, key: str) -> int:
        """Segundos até a chave poder tentar de novo (0 se não estiver bloqueada)."""
        now = time.monotonic()
        with self._lock:
            events = self._prune(key, now)
            if len(events) < self.max_failures:
                return 0
            return max(1, int(self.window_seconds - (now - events[0])) + 1)

    def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._failures[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()
