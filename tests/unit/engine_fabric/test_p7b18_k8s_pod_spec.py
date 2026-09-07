"""
P7B.18 -- Kubernetes worker pod spec: positive + hostile matrix (privileged, hostPath,
hostNetwork, missing limits, secret leakage into labels).
"""

import pytest

from akaalEngine.fabric.k8s_runtime.pod_spec import (
    ConfigMapVolumeSource,
    EmptyDirVolumeSource,
    PodSpecValidationError,
    ResourceRequirements,
    SecretReference,
    SecretVolumeSource,
    build_worker_pod_spec,
)


def _resources():
    return ResourceRequirements(cpu_request="500m", memory_request="512Mi", cpu_limit="1", memory_limit="1Gi")


def test_minimal_valid_spec_has_secure_defaults():
    spec = build_worker_pod_spec(pod_name="worker-1", namespace="akaal", image="akaal/worker:1.0.0",
                                  resources=_resources(), service_account_name="akaal-worker-sa")
    sc = spec["spec"]["containers"][0]["securityContext"]
    assert sc["privileged"] is False
    assert sc["runAsNonRoot"] is True
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["readOnlyRootFilesystem"] is True
    assert sc["capabilities"]["drop"] == ["ALL"]
    assert "hostNetwork" not in spec["spec"]
    assert "hostPID" not in spec["spec"]
    assert "hostIPC" not in spec["spec"]


def test_secret_reference_renders_as_secretkeyref_never_literal_value():
    ref = SecretReference(env_var_name="DB_PASSWORD", secret_name="db-creds", secret_key="password")
    spec = build_worker_pod_spec(pod_name="worker-1", namespace="akaal", image="img:1", resources=_resources(),
                                  service_account_name="sa", secret_refs=(ref,))
    env = spec["spec"]["containers"][0]["env"]
    assert env[0]["valueFrom"]["secretKeyRef"] == {"name": "db-creds", "key": "password"}
    assert "value" not in env[0]  # never a literal value key


def test_secret_volume_mounted_readonly():
    vol = SecretVolumeSource(volume_name="tls-certs", secret_name="worker-tls", mount_path="/etc/tls")
    spec = build_worker_pod_spec(pod_name="worker-1", namespace="akaal", image="img:1", resources=_resources(),
                                  service_account_name="sa", volumes=(vol,))
    mount = spec["spec"]["containers"][0]["volumeMounts"][0]
    assert mount["readOnly"] is True
    assert spec["spec"]["volumes"][0]["secret"]["secretName"] == "worker-tls"


def test_configmap_volume_never_treated_as_secret():
    vol = ConfigMapVolumeSource(volume_name="cfg", config_map_name="worker-config", mount_path="/etc/config")
    spec = build_worker_pod_spec(pod_name="worker-1", namespace="akaal", image="img:1", resources=_resources(),
                                  service_account_name="sa", volumes=(vol,))
    assert "configMap" in spec["spec"]["volumes"][0]
    assert "secret" not in spec["spec"]["volumes"][0]


def test_emptydir_volume_writable():
    vol = EmptyDirVolumeSource(volume_name="scratch", mount_path="/scratch", size_limit="2Gi")
    spec = build_worker_pod_spec(pod_name="worker-1", namespace="akaal", image="img:1", resources=_resources(),
                                  service_account_name="sa", volumes=(vol,))
    mount = spec["spec"]["containers"][0]["volumeMounts"][0]
    assert mount["readOnly"] is False


# ------------------------------------------------------------------ hostile: structural impossibility


def test_no_way_to_request_privileged_hostnetwork_hostpid_hostipc_or_hostpath():
    """There is no keyword argument anywhere in build_worker_pod_spec's signature for
    any of these -- proven by introspecting the actual function signature, not just by
    checking the output of one call (which could miss an unused-but-present parameter)."""
    import inspect
    sig = inspect.signature(build_worker_pod_spec)
    forbidden = {"privileged", "host_network", "hostNetwork", "host_pid", "hostPID",
                 "host_ipc", "hostIPC", "host_path", "hostPath"}
    assert forbidden.isdisjoint(sig.parameters.keys())


def test_no_hostpath_volume_source_type_exists_in_module():
    import akaalEngine.fabric.k8s_runtime.pod_spec as mod
    assert not hasattr(mod, "HostPathVolumeSource")


# ------------------------------------------------------------------ hostile: missing/invalid inputs


def test_missing_resource_limit_rejected_at_construction():
    with pytest.raises(PodSpecValidationError):
        ResourceRequirements(cpu_request="500m", memory_request="512Mi", cpu_limit="", memory_limit="1Gi")


def test_empty_service_account_rejected_no_default_sa():
    with pytest.raises(PodSpecValidationError):
        build_worker_pod_spec(pod_name="w1", namespace="akaal", image="img:1", resources=_resources(), service_account_name="")


def test_run_as_root_rejected():
    with pytest.raises(PodSpecValidationError):
        build_worker_pod_spec(pod_name="w1", namespace="akaal", image="img:1", resources=_resources(),
                               service_account_name="sa", run_as_user=0)


def test_invalid_pod_name_rejected():
    with pytest.raises(PodSpecValidationError):
        build_worker_pod_spec(pod_name="Invalid_Name!", namespace="akaal", image="img:1", resources=_resources(), service_account_name="sa")


def test_invalid_namespace_rejected():
    with pytest.raises(PodSpecValidationError):
        build_worker_pod_spec(pod_name="w1", namespace="Bad Namespace", image="img:1", resources=_resources(), service_account_name="sa")


def test_empty_image_rejected():
    with pytest.raises(PodSpecValidationError):
        build_worker_pod_spec(pod_name="w1", namespace="akaal", image="", resources=_resources(), service_account_name="sa")


def test_invalid_restart_policy_rejected():
    with pytest.raises(PodSpecValidationError):
        build_worker_pod_spec(pod_name="w1", namespace="akaal", image="img:1", resources=_resources(),
                               service_account_name="sa", restart_policy="Sometimes")


def test_duplicate_volume_names_rejected():
    v1 = EmptyDirVolumeSource(volume_name="dup", mount_path="/a")
    v2 = EmptyDirVolumeSource(volume_name="dup", mount_path="/b")
    with pytest.raises(PodSpecValidationError):
        build_worker_pod_spec(pod_name="w1", namespace="akaal", image="img:1", resources=_resources(),
                               service_account_name="sa", volumes=(v1, v2))


def test_secret_looking_label_value_rejected():
    with pytest.raises(PodSpecValidationError):
        build_worker_pod_spec(pod_name="w1", namespace="akaal", image="img:1", resources=_resources(),
                               service_account_name="sa", labels={"note": "my-password-is-hunter2"})


def test_empty_secret_reference_fields_rejected():
    with pytest.raises(PodSpecValidationError):
        SecretReference(env_var_name="", secret_name="s", secret_key="k")
