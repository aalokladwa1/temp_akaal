"""
akaalEngine.extensions.sandbox.windows_job
=============================================
Real Windows process-resource containment via Win32 Job Objects (ctypes, no third-party
dependency). Closes the previously-honest-but-real gap where memory/CPU budgets were
accepted on Windows but not enforced -- POSIX had `resource.setrlimit`, Windows had nothing.

A Job Object is the correct native Windows primitive for this: assigning a process (and,
transitively, any child processes it spawns) to a job lets the OS itself enforce a hard
per-job memory ceiling and guarantees the whole process tree dies if the job handle closes
(JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) -- stronger containment than the parent process
tracking children itself, since it holds even if this Python process crashes.

Windows-only. Importing this module on a non-Windows platform raises ImportError at import
time (via the `ctypes.wintypes`/`ctypes.windll` import failing) rather than silently
no-op'ing -- callers must platform-guard before importing it (see process_isolation.py).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# --- Win32 constants ---
JobObjectExtendedLimitInformation = 9
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
PROCESS_ALL_ACCESS = 0x1F0FFF


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_void_p),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class WindowsJobObjectError(RuntimeError):
    """Raised when a Win32 Job Object API call fails."""


class WindowsJobObject:
    """
    Wraps one Win32 Job Object. Assign a child process to it (by PID) to place a real,
    OS-enforced ceiling on that process's (and its descendants') memory usage, and to
    guarantee the whole tree is killed if this job object's handle is closed.
    """

    def __init__(self, memory_limit_bytes: int = None, active_process_limit: int = None) -> None:
        self._handle = kernel32.CreateJobObjectW(None, None)
        if not self._handle:
            raise WindowsJobObjectError(f"CreateJobObjectW failed: {ctypes.WinError(ctypes.get_last_error())}")

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if memory_limit_bytes is not None:
            info.ProcessMemoryLimit = memory_limit_bytes
            flags |= JOB_OBJECT_LIMIT_PROCESS_MEMORY
        if active_process_limit is not None:
            info.BasicLimitInformation.ActiveProcessLimit = active_process_limit
            flags |= JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        info.BasicLimitInformation.LimitFlags = flags

        ok = kernel32.SetInformationJobObject(
            self._handle,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            err = ctypes.WinError(ctypes.get_last_error())
            kernel32.CloseHandle(self._handle)
            raise WindowsJobObjectError(f"SetInformationJobObject failed: {err}")

    def assign_process(self, pid: int) -> None:
        proc_handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not proc_handle:
            raise WindowsJobObjectError(f"OpenProcess({pid}) failed: {ctypes.WinError(ctypes.get_last_error())}")
        try:
            ok = kernel32.AssignProcessToJobObject(self._handle, proc_handle)
            if not ok:
                raise WindowsJobObjectError(
                    f"AssignProcessToJobObject failed for pid={pid}: {ctypes.WinError(ctypes.get_last_error())}"
                )
        finally:
            kernel32.CloseHandle(proc_handle)

    def terminate(self) -> None:
        """Kills every process currently in this job (immediate, unconditional)."""
        kernel32.TerminateJobObject(self._handle, 1)

    def close(self) -> None:
        """
        Closes the job handle. Because JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE was set, if this
        was the last handle to the job, every process still assigned to it is killed by the
        OS as part of closing it -- this is the real containment guarantee, not just an
        advisory close.
        """
        if self._handle:
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> "WindowsJobObject":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
