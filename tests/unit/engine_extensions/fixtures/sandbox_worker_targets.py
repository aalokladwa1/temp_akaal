"""
Target callables imported by the SubprocessSandbox worker process during hostile tests.
Deliberately outside the sandbox module itself -- these represent "extension code."
"""

import os
import time


def echo(payload):
    return {"echoed": payload}


def crash(payload):
    raise RuntimeError("intentional extension crash for hostile sandbox test")


def hang_forever(payload):
    time.sleep(3600)
    return {"should": "never reach here"}


def read_env_var(payload):
    var_name = payload["var_name"]
    return {"value": os.environ.get(var_name)}


def crash_the_process_outright(payload):
    os._exit(139)  # simulate a hard native crash (e.g. segfault-equivalent exit code), not a Python exception


def read_secret(payload, secrets):
    ref = payload["secret_ref"]
    return {"value": secrets.get(ref)}


def allocate_and_touch_memory(payload):
    """Allocates and actually writes to `mb` megabytes to force real (not just reserved) commit."""
    mb = payload.get("mb", 512)
    chunk = bytearray(mb * 1024 * 1024)
    for i in range(0, len(chunk), 4096):
        chunk[i] = 1  # touch each page so the OS actually commits it, not just reserves address space
    return {"allocated_mb": mb}


def write_marker_file(payload):
    """A real, observable side effect -- used to prove a denied execution never runs at all."""
    path = payload["path"]
    with open(path, "w") as f:
        f.write("sentinel: this extension code ran")
    return {"wrote": path}
