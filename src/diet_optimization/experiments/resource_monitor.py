"""Low-overhead sampled resident-memory monitor for one optimizer execution."""

from __future__ import annotations

import ctypes
import os
import platform
import threading


def _current_process_rss_bytes() -> int | None:
    """Return current process resident memory where the OS exposes it cheaply."""
    system = platform.system()
    if system == "Windows":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        get_process = kernel32.GetCurrentProcess
        get_process.restype = ctypes.c_void_p
        get_memory = psapi.GetProcessMemoryInfo
        get_memory.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessMemoryCounters), ctypes.c_ulong]
        get_memory.restype = ctypes.c_int
        if get_memory(get_process(), ctypes.byref(counters), counters.cb):
            return int(counters.WorkingSetSize)
        return None

    if os.path.exists("/proc/self/statm"):
        try:
            with open("/proc/self/statm", encoding="ascii") as statm:
                resident_pages = int(statm.read().split()[1])
            return resident_pages * int(os.sysconf("SC_PAGE_SIZE"))
        except (OSError, ValueError, IndexError):
            return None
    return None


class SampledProcessMemory:
    """Sample working set/RSS while the wrapped optimization is running."""

    def __init__(self, interval_seconds: float = 0.1) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._baseline: int | None = None
        self._peak: int | None = None
        self._samples = 0

    def _sample_loop(self) -> None:
        while not self._stop.is_set():
            value = _current_process_rss_bytes()
            if value is not None:
                self._samples += 1
                self._peak = value if self._peak is None else max(self._peak, value)
            self._stop.wait(self.interval_seconds)

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("memory sampler has already been started")
        self._baseline = _current_process_rss_bytes()
        if self._baseline is not None:
            self._peak = self._baseline
            self._samples = 1
        self._thread = threading.Thread(target=self._sample_loop, name="process-memory-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, int | float | str | None]:
        if self._thread is None:
            raise RuntimeError("memory sampler has not been started")
        self._stop.set()
        self._thread.join()
        return {
            "measurement": "sampled_process_rss_100ms",
            "sampling_interval_seconds": self.interval_seconds,
            "baseline_rss_bytes": self._baseline,
            "peak_sampled_rss_bytes": self._peak,
            "sampled_peak_increase_bytes": (
                max(0, self._peak - self._baseline)
                if self._peak is not None and self._baseline is not None else None
            ),
            "sample_count": self._samples,
        }
