"""
akaalEngine.fabric.k8s_runtime.pod_spec
===========================================
P7B.18 -- Worker pod spec construction with STRUCTURALLY enforced secure defaults.

Unlike a typical "secure by convention" builder, several unsafe primitives are not merely
defaulted off here -- they have NO parameter at all, so there is no way to call this
module and produce a privileged/hostNetwork/hostPID/hostIPC/hostPath pod spec:

  * No `privileged`, `hostNetwork`, `hostPID`, or `hostIPC` parameter exists anywhere in
    this module's public API.
  * The only supported volume sources are `SecretVolumeSource` and `ConfigMapVolumeSource`
    (secret/configmap references) and `EmptyDirVolumeSource` -- there is no
    `HostPathVolumeSource` type in this module at all.
  * `SecretReference` never carries a literal secret value -- only
    `(env_var_name, secret_name, secret_key)`, rendered as a Kubernetes
    `valueFrom.secretKeyRef`, exactly mirroring how the rest of this codebase's Secrets
    integration (P7B.4's `SecretResolverCallback`) already never carries resolved secret
    material into a spec/log/CRD.
  * `ResourceRequirements`' four fields are all mandatory (not `Optional`) -- a caller
    cannot construct a pod spec without explicit CPU/memory requests AND limits.

Kubernetes is one ExecutionSite substrate among four (see package docstring) -- nothing
here is invoked unconditionally; a caller only reaches this module after Campaign C
placement has already selected a `SiteKind.KUBERNETES` site.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple, Union


class PodSpecValidationError(ValueError):
    pass


_DNS_1123_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


def _validate_dns1123(value: str, field_name: str) -> None:
    if not value or len(value) > 253 or not _DNS_1123_RE.match(value):
        raise PodSpecValidationError(f"{field_name}={value!r} must be a valid DNS-1123 label/subdomain.")


@dataclass(frozen=True)
class ResourceRequirements:
    """All four fields mandatory -- see module docstring."""
    cpu_request: str
    memory_request: str
    cpu_limit: str
    memory_limit: str

    def __post_init__(self) -> None:
        for name in ("cpu_request", "memory_request", "cpu_limit", "memory_limit"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise PodSpecValidationError(f"ResourceRequirements.{name} must be non-empty.")

    def to_dict(self) -> Dict[str, Dict[str, str]]:
        return {
            "requests": {"cpu": self.cpu_request, "memory": self.memory_request},
            "limits": {"cpu": self.cpu_limit, "memory": self.memory_limit},
        }


@dataclass(frozen=True)
class SecretReference:
    """Never carries a literal secret value -- see module docstring."""
    env_var_name: str
    secret_name: str
    secret_key: str

    def __post_init__(self) -> None:
        for name in ("env_var_name", "secret_name", "secret_key"):
            if not getattr(self, name) or not getattr(self, name).strip():
                raise PodSpecValidationError(f"SecretReference.{name} must be non-empty.")

    def to_env_entry(self) -> Dict[str, Any]:
        return {"name": self.env_var_name, "valueFrom": {"secretKeyRef": {"name": self.secret_name, "key": self.secret_key}}}


@dataclass(frozen=True)
class SecretVolumeSource:
    volume_name: str
    secret_name: str
    mount_path: str


@dataclass(frozen=True)
class ConfigMapVolumeSource:
    """NON-SECRET configuration only -- callers must never place secret material in a
    ConfigMap; this module cannot detect that misuse by content inspection (that would be
    both unreliable and out of scope) but structurally never accepts a "value", only a
    reference to an already-existing ConfigMap name."""
    volume_name: str
    config_map_name: str
    mount_path: str


@dataclass(frozen=True)
class EmptyDirVolumeSource:
    volume_name: str
    mount_path: str
    size_limit: Optional[str] = None


VolumeSource = Union[SecretVolumeSource, ConfigMapVolumeSource, EmptyDirVolumeSource]

_FORBIDDEN_LABEL_SUBSTRINGS = ("password", "secret", "token", "apikey", "api_key", "private_key")


def _validate_labels(labels: Mapping[str, str]) -> None:
    for key, value in labels.items():
        lowered_value = (value or "").lower()
        if any(bad in lowered_value for bad in _FORBIDDEN_LABEL_SUBSTRINGS):
            raise PodSpecValidationError(
                f"Label {key!r} value looks like it may contain sensitive material "
                f"(matched a forbidden substring); labels/annotations must never carry "
                f"secret material -- use a SecretReference instead."
            )


def build_worker_pod_spec(
    *,
    pod_name: str,
    namespace: str,
    image: str,
    resources: ResourceRequirements,
    service_account_name: str,
    labels: Optional[Mapping[str, str]] = None,
    secret_refs: Tuple[SecretReference, ...] = (),
    volumes: Tuple[VolumeSource, ...] = (),
    node_selector: Optional[Mapping[str, str]] = None,
    tolerations: Tuple[Mapping[str, str], ...] = (),
    termination_grace_period_seconds: int = 30,
    restart_policy: str = "Always",
    run_as_user: int = 65532,
    run_as_group: int = 65532,
) -> Dict[str, Any]:
    """
    Returns a plain dict Pod spec (not YAML, not a live API call). Secure defaults are
    unconditional, not caller-toggleable: `runAsNonRoot: true`, `allowPrivilegeEscalation:
    false`, `readOnlyRootFilesystem: true`, `capabilities.drop: ["ALL"]`,
    `privileged` is never emitted as true (there is no parameter to set it true).
    """
    _validate_dns1123(pod_name, "pod_name")
    _validate_dns1123(namespace, "namespace")
    if not image or not image.strip():
        raise PodSpecValidationError("image must be non-empty.")
    if not service_account_name or not service_account_name.strip():
        raise PodSpecValidationError("service_account_name must be non-empty (no default service account).")
    if run_as_user == 0 or run_as_group == 0:
        raise PodSpecValidationError("run_as_user/run_as_group must not be 0 (root) -- runAsNonRoot is unconditional here.")
    if restart_policy not in ("Always", "OnFailure", "Never"):
        raise PodSpecValidationError(f"restart_policy must be a valid Kubernetes value; got {restart_policy!r}.")
    if termination_grace_period_seconds < 0:
        raise PodSpecValidationError("termination_grace_period_seconds must be >= 0.")

    labels = dict(labels or {})
    _validate_labels(labels)

    volume_mounts = []
    volume_defs = []
    seen_volume_names = set()
    for v in volumes:
        if v.volume_name in seen_volume_names:
            raise PodSpecValidationError(f"Duplicate volume_name: {v.volume_name!r}")
        seen_volume_names.add(v.volume_name)
        volume_mounts.append({"name": v.volume_name, "mountPath": v.mount_path, "readOnly": not isinstance(v, EmptyDirVolumeSource)})
        if isinstance(v, SecretVolumeSource):
            volume_defs.append({"name": v.volume_name, "secret": {"secretName": v.secret_name}})
        elif isinstance(v, ConfigMapVolumeSource):
            volume_defs.append({"name": v.volume_name, "configMap": {"name": v.config_map_name}})
        elif isinstance(v, EmptyDirVolumeSource):
            ed: Dict[str, Any] = {}
            if v.size_limit:
                ed["sizeLimit"] = v.size_limit
            volume_defs.append({"name": v.volume_name, "emptyDir": ed})
        else:  # pragma: no cover -- exhaustive by VolumeSource's closed Union
            raise PodSpecValidationError(f"Unsupported volume source type: {type(v).__name__}")

    container: Dict[str, Any] = {
        "name": "akaal-worker",
        "image": image,
        "resources": resources.to_dict(),
        "env": [ref.to_env_entry() for ref in secret_refs],
        "volumeMounts": volume_mounts,
        "securityContext": {
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": True,
            "runAsNonRoot": True,
            "runAsUser": run_as_user,
            "runAsGroup": run_as_group,
            "capabilities": {"drop": ["ALL"]},
            "privileged": False,
            "seccompProfile": {"type": "RuntimeDefault"},
        },
    }

    pod_spec: Dict[str, Any] = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": pod_name, "namespace": namespace, "labels": labels},
        "spec": {
            "serviceAccountName": service_account_name,
            "automountServiceAccountToken": True,
            "securityContext": {"runAsNonRoot": True, "runAsUser": run_as_user, "runAsGroup": run_as_group, "fsGroup": run_as_group},
            "containers": [container],
            "volumes": volume_defs,
            "restartPolicy": restart_policy,
            "terminationGracePeriodSeconds": termination_grace_period_seconds,
        },
    }
    if node_selector:
        pod_spec["spec"]["nodeSelector"] = dict(node_selector)
    if tolerations:
        pod_spec["spec"]["tolerations"] = [dict(t) for t in tolerations]

    return pod_spec
