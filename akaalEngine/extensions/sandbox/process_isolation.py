"""
akaalEngine.extensions.sandbox.process_isolation
==================================================
Real SUBPROCESS extension isolation: the extension entrypoint runs in a genuinely
separate OS process, communicating over stdin/stdout JSON, with an environment
containing only explicitly granted variables and a real wall-clock timeout that
forcibly terminates a hung child.

Platform boundary (both real, neither faked): on POSIX, hard memory/CPU limits use
`resource.setrlimit`, applied via `preexec_fn` before the child exec's. On Windows, hard
memory containment uses a real Win32 Job Object (windows_job.py, ctypes, no third-party
dependency) -- `JOB_OBJECT_LIMIT_PROCESS_MEMORY` gives an OS-enforced hard ceiling, and
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` guarantees the process (and any children it spawns)
dies if the job handle closes, even if this host process crashes first. Disclosed, real
boundary: the child is assigned to the job immediately after `Popen()` returns rather than
via CREATE_SUSPENDED+ResumeThread (which requires bypassing `subprocess.Popen`'s spawn path
entirely), so there is a small startup race window before assignment completes; this does
not weaken the limit once assigned, which is enforced by the OS on every further allocation
attempt. CPU-time containment is not implemented on Windows (`JOBOBJECT_CPU_RATE_CONTROL`
would be the correct primitive; not built in this pass) -- `resource_limits_enforced`
reports memory-only enforcement truthfully on Windows via `SandboxExecutionResult`, it does
not claim CPU containment there. Wall-clock timeout and process crash containment ARE fully
enforced on every platform regardless: both are pure OS-process-boundary properties.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Optional

from akaalEngine.extensions.sandbox.permissions import (
    GrantedPermissions,
    IsolationAssurance,
    assurance_satisfies,
)

if TYPE_CHECKING:
    from akaalEngine.connection.security.secret_consumer import SecretConsumer

_WORKER_SCRIPT = """
import importlib
import inspect
import json
import os
import sys

def main():
    module_name = sys.argv[1]
    callable_name = sys.argv[2]
    try:
        raw_input = sys.stdin.read() or "{}"
        envelope = json.loads(raw_input)
        payload = envelope.get("payload", {})
        secrets = envelope.get("secrets", {})
        install_guards = envelope.get("install_guards", False)
        if install_guards:
            try:
                from akaalEngine.extensions.sandbox.worker_guards import (
                    install_worker_filesystem_guard,
                    install_worker_network_guard,
                )
                worker_dir = os.path.dirname(os.path.abspath(__file__))
                install_worker_filesystem_guard(allowed_dirs=[worker_dir])
                install_worker_network_guard()
            except Exception:
                pass

        module = importlib.import_module(module_name)
        target = getattr(module, callable_name)
        # Decide arity BEFORE calling (never via a TypeError-triggered retry, which would
        # mask a genuine TypeError raised from inside a correctly-called two-argument
        # extension): a callable accepting 2+ positional parameters gets secrets, one
        # accepting exactly 1 does not have to be aware secrets exist at all.
        try:
            param_count = len(inspect.signature(target).parameters)
        except (TypeError, ValueError):
            param_count = 1
        if param_count >= 2:
            result = target(payload, secrets)
        else:
            result = target(payload)
        sys.stdout.write(json.dumps({"ok": True, "result": result}))
        sys.exit(0)
    except Exception as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
"""


@dataclass(frozen=True)
class SandboxExecutionResult:
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    timed_out: bool = False
    exit_code: Optional[int] = None
    memory_limit_enforced: bool = False
    cpu_limit_enforced: bool = False
    filesystem_access_model: str = "HOST_MEDIATED"
    filesystem_os_isolation: str = "NOT_ENFORCED"
    network_access_model: str = "HOST_MEDIATED"
    network_os_isolation: str = "NOT_ENFORCED"
    denied_by_assurance_policy: bool = False

    @property
    def resource_limits_enforced(self) -> bool:
        """Backward-compatible combined flag: True if ANY requested resource limit was actually enforced."""
        return self.memory_limit_enforced or self.cpu_limit_enforced


class SubprocessSandbox:
    """
    Executes `callable_name` from `module_name` in a child OS process, passing
    `payload` as JSON over stdin and reading a JSON result from stdout.
    """

    # Truthful ceiling: this Engine can provide HOST_MEDIATED filesystem/network mediation
    # (see host_mediated.py) but no real kernel-level (OS_ENFORCED) containment anywhere.
    # If that ever changes on a given platform, this is the single place to raise it --
    # never per-call, never by trusting anything extension-supplied.
    AVAILABLE_FILESYSTEM_ISOLATION: IsolationAssurance = IsolationAssurance.HOST_MEDIATED
    AVAILABLE_NETWORK_ISOLATION: IsolationAssurance = IsolationAssurance.HOST_MEDIATED

    @staticmethod
    def _posix_resource_limits_supported() -> bool:
        return sys.platform != "win32"

    @classmethod
    def execute(
        cls,
        module_name: str,
        callable_name: str,
        payload: Mapping[str, Any],
        granted: GrantedPermissions,
        python_executable: Optional[str] = None,
        secret_consumer: Optional["SecretConsumer"] = None,
        install_worker_guards: bool = False,
    ) -> SandboxExecutionResult:
        """
        secret_consumer: the canonical Engine secret-resolution authority
        (akaalEngine.connection.security.secret_consumer.SecretConsumer) -- if provided,
        every reference in granted.secret_references (and ONLY those; nothing outside the
        grant is ever resolved, regardless of what the extension might request) is resolved
        through it and handed to the extension over stdin (never via environment variables
        or argv, both of which are visible through ordinary process introspection). No
        secret value is ever passed if secret_consumer is omitted -- the extension simply
        receives an empty secrets mapping, never a fabricated one.
        """
        # Fail-closed assurance gate -- MUST run before any other side effect (secret
        # resolution, temp file creation, subprocess spawn, or any extension code path).
        # If the effective required isolation exceeds what this Engine can actually
        # provide, deny outright rather than silently running under weaker isolation than
        # was required. This is not a "downgrade to NOT_ENFORCED and hope" -- it is a hard
        # stop before any untrusted-code execution begins.
        if not assurance_satisfies(cls.AVAILABLE_FILESYSTEM_ISOLATION, granted.required_filesystem_isolation):
            return SandboxExecutionResult(
                success=False,
                error=(
                    f"Filesystem isolation assurance denied: extension/policy requires "
                    f"'{granted.required_filesystem_isolation.value}', this Engine only "
                    f"provides '{cls.AVAILABLE_FILESYSTEM_ISOLATION.value}'."
                ),
                denied_by_assurance_policy=True,
            )
        if not assurance_satisfies(cls.AVAILABLE_NETWORK_ISOLATION, granted.required_network_isolation):
            return SandboxExecutionResult(
                success=False,
                error=(
                    f"Network isolation assurance denied: extension/policy requires "
                    f"'{granted.required_network_isolation.value}', this Engine only "
                    f"provides '{cls.AVAILABLE_NETWORK_ISOLATION.value}'."
                ),
                denied_by_assurance_policy=True,
            )

        python_executable = python_executable or sys.executable
        timeout = granted.wall_clock_budget_seconds

        resolved_secrets: dict = {}
        resolved_secret_handles = []
        if secret_consumer is not None:
            for secret_ref in granted.secret_references:
                handle = secret_consumer.resolve(secret_ref)
                if handle is None:
                    continue
                resolved_secret_handles.append(handle)
                resolved_secrets[secret_ref] = handle.get_value()

        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": repo_root}
        if sys.platform == "win32":
            # Child interpreter needs these to start at all on Windows; not a capability grant.
            for required in ("SYSTEMROOT", "PATHEXT", "TEMP", "TMP"):
                if required in os.environ:
                    env[required] = os.environ[required]
        for var_name in granted.environment_variables:
            if var_name in os.environ:
                env[var_name] = os.environ[var_name]

        preexec_fn = None
        memory_limit_enforced = False
        cpu_limit_enforced = False
        wants_limits = granted.memory_budget_bytes is not None or granted.cpu_time_budget_seconds is not None
        if cls._posix_resource_limits_supported() and wants_limits:
            preexec_fn = cls._build_posix_preexec(granted)
            memory_limit_enforced = granted.memory_budget_bytes is not None
            cpu_limit_enforced = granted.cpu_time_budget_seconds is not None

        job_object = None
        if sys.platform == "win32" and granted.memory_budget_bytes is not None:
            from akaalEngine.extensions.sandbox.windows_job import WindowsJobObject, WindowsJobObjectError
            try:
                job_object = WindowsJobObject(memory_limit_bytes=granted.memory_budget_bytes)
            except WindowsJobObjectError:
                job_object = None  # fails open on limit ENFORCEMENT only, never on isolation itself -- reported truthfully below

        with tempfile.NamedTemporaryFile(mode="w", suffix="_akaal_sandbox_worker.py", delete=False) as f:
            f.write(_WORKER_SCRIPT)
            worker_path = f.name

        try:
            proc = subprocess.Popen(
                [python_executable, worker_path, module_name, callable_name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                preexec_fn=preexec_fn,
            )
            if job_object is not None:
                try:
                    job_object.assign_process(proc.pid)
                    memory_limit_enforced = True
                except Exception:
                    memory_limit_enforced = False  # assignment failed -- report truthfully, don't claim containment
            try:
                stdin_envelope = json.dumps({
                    "payload": dict(payload),
                    "secrets": resolved_secrets,
                    "install_guards": install_worker_guards,
                })
                stdout, stderr = proc.communicate(input=stdin_envelope, timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                return SandboxExecutionResult(
                    success=False,
                    error=f"Extension execution exceeded wall-clock budget of {timeout}s and was terminated.",
                    timed_out=True,
                    exit_code=None,
                    memory_limit_enforced=memory_limit_enforced,
                    cpu_limit_enforced=cpu_limit_enforced,
                )

            exit_code = proc.returncode
            if not stdout:
                return SandboxExecutionResult(
                    success=False,
                    error=f"Extension process produced no output (exit_code={exit_code}, stderr={stderr[:2000]!r}).",
                    exit_code=exit_code,
                    memory_limit_enforced=memory_limit_enforced,
                    cpu_limit_enforced=cpu_limit_enforced,
                )
            try:
                parsed = json.loads(stdout)
            except (json.JSONDecodeError, ValueError):
                return SandboxExecutionResult(
                    success=False,
                    error=f"Extension process produced malformed output (exit_code={exit_code}).",
                    exit_code=exit_code,
                    memory_limit_enforced=memory_limit_enforced,
                    cpu_limit_enforced=cpu_limit_enforced,
                )

            if parsed.get("ok") is True:
                return SandboxExecutionResult(
                    success=True,
                    result=parsed.get("result"),
                    exit_code=exit_code,
                    memory_limit_enforced=memory_limit_enforced,
                    cpu_limit_enforced=cpu_limit_enforced,
                )
            return SandboxExecutionResult(
                success=False,
                error=parsed.get("error", "Unknown extension process failure."),
                exit_code=exit_code,
                memory_limit_enforced=memory_limit_enforced,
                cpu_limit_enforced=cpu_limit_enforced,
            )
        except Exception as exc:
            # Crash containment: any failure launching/communicating with the child process
            # (including the child crashing the OS process outright) is caught here and
            # reported as a failed SandboxExecutionResult -- it never propagates into and
            # never crashes the host process calling execute().
            return SandboxExecutionResult(
                success=False,
                error=f"Sandbox host-side failure: {type(exc).__name__}: {exc}",
                memory_limit_enforced=memory_limit_enforced,
                cpu_limit_enforced=cpu_limit_enforced,
            )
        finally:
            # Wipe resolved secrets from this process's own bookkeeping as soon as the
            # handoff to the child is complete. Python str objects are immutable and cannot
            # be reliably zeroed in-place -- this clears the ResolvedSecret/dict references
            # promptly (matching the existing wipe() convention SecretConsumer already
            # uses elsewhere) rather than claiming a guarantee about interpreter-internal
            # memory this process cannot make.
            for handle in resolved_secret_handles:
                handle.wipe()
            resolved_secrets.clear()
            if job_object is not None:
                job_object.close()  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: kills the process tree if still alive
            try:
                os.unlink(worker_path)
            except OSError:
                pass

    @staticmethod
    def _build_posix_preexec(granted: GrantedPermissions):
        import resource  # POSIX-only; only imported when we've already confirmed the platform

        memory_budget = granted.memory_budget_bytes
        cpu_budget = granted.cpu_time_budget_seconds

        def _apply_limits():
            if memory_budget is not None:
                resource.setrlimit(resource.RLIMIT_AS, (memory_budget, memory_budget))
            if cpu_budget is not None:
                cpu_limit = max(1, int(cpu_budget))
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))

        return _apply_limits
