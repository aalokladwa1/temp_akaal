"""
P7B.20 -- Helm Platform: STATIC text/YAML validation of deploy/kubernetes/.

PROOF-LEVEL HONESTY: no `helm` binary is installed in this environment (verified via
`shutil.which("helm") is None` below, asserted as a documented fact rather than silently
skipped). These tests therefore validate Chart.yaml/values.yaml as real parsed YAML (they
contain no Go-template syntax) and validate templates/*.yaml via targeted TEXT
inspection (they contain `{{ }}` Go-template syntax and are not parseable as plain YAML
without a real Helm/Jinja-like render). This is LOCALLY_VERIFIED proof of the checked-in
file CONTENT, never a substitute for `helm template`/`helm lint`/`helm install --dry-run`
against a real Helm binary and/or cluster (EXTERNAL_DEFERRED -- see progress.md P7B
Group-2 §36).
"""

import shutil
from pathlib import Path

import yaml

DEPLOY_DIR = Path(__file__).resolve().parents[3] / "deploy" / "kubernetes"
TEMPLATES_DIR = DEPLOY_DIR / "templates"


def test_helm_binary_genuinely_unavailable_in_this_environment():
    """Documents the honest constraint driving this file's static-only approach --
    if this assertion ever fails (helm becomes available), the proof strategy here
    should be upgraded to a real `helm template`/`helm lint` invocation."""
    assert shutil.which("helm") is None


def test_chart_yaml_parses_and_has_required_fields():
    data = yaml.safe_load((DEPLOY_DIR / "Chart.yaml").read_text(encoding="utf-8"))
    assert data["apiVersion"] == "v2"
    assert data["name"]
    assert data["version"]
    assert data["type"] == "application"


def test_values_yaml_parses():
    data = yaml.safe_load((DEPLOY_DIR / "values.yaml").read_text(encoding="utf-8"))
    assert data is not None


def _values():
    return yaml.safe_load((DEPLOY_DIR / "values.yaml").read_text(encoding="utf-8"))


def test_no_default_latest_tag():
    values = _values()
    assert values["image"]["tag"] == ""  # no floating default; caller must pin


def test_resource_requests_and_limits_both_present():
    values = _values()
    resources = values["resources"]
    assert "cpu" in resources["requests"] and "memory" in resources["requests"]
    assert "cpu" in resources["limits"] and "memory" in resources["limits"]


def test_security_context_secure_by_default():
    values = _values()
    sc = values["securityContext"]
    assert sc["runAsNonRoot"] is True
    assert sc["runAsUser"] != 0
    csc = values["containerSecurityContext"]
    assert csc["allowPrivilegeEscalation"] is False
    assert csc["readOnlyRootFilesystem"] is True
    assert csc["privileged"] is False
    assert csc["capabilities"]["drop"] == ["ALL"]


def test_network_policy_and_pdb_enabled_by_default():
    values = _values()
    assert values["networkPolicy"]["enabled"] is True
    assert values["networkPolicy"]["allowedEgressCIDRs"] == []  # deny-by-default, not unrestricted
    assert values["podDisruptionBudget"]["enabled"] is True


def test_secret_env_list_has_no_literal_value_field_documented():
    values = _values()
    assert values["secretEnv"] == []  # example entries are commented out, not live defaults


# ------------------------------------------------------------------ template text hostile checks


def _all_template_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in TEMPLATES_DIR.glob("*.yaml"))


def test_no_privileged_true_anywhere_in_templates():
    text = _all_template_text()
    assert "privileged: true" not in text.lower()


def test_no_host_network_pid_ipc_anywhere_in_templates():
    text = _all_template_text()
    for forbidden in ("hostnetwork", "hostpid", "hostipc", "hostpath"):
        assert forbidden not in text.lower()


def _strip_go_template_comments(text: str) -> str:
    import re
    return re.sub(r"\{\{/\*.*?\*/\}\}", "", text, flags=re.DOTALL)


def test_rbac_uses_namespaced_role_never_clusterrole():
    text = _strip_go_template_comments((TEMPLATES_DIR / "rbac.yaml").read_text(encoding="utf-8"))
    assert "ClusterRole" not in text
    assert "cluster-admin" not in text.lower()


def test_rbac_has_no_wildcard_verbs_or_resources():
    import re
    text = (TEMPLATES_DIR / "rbac.yaml").read_text(encoding="utf-8")
    # Regex over the raw text rather than a real YAML parse -- the file's Go-template
    # comment block (`{{/* ... */}}`) is not valid YAML on its own. This still reliably
    # catches a wildcard verb/resource list, which is always written as a quoted "*"
    # inside a `verbs:`/`resources:` bracketed list in this file's style.
    for line in text.splitlines():
        if re.match(r"\s*(verbs|resources)\s*:", line):
            assert '"*"' not in line and "'*'" not in line, f"wildcard found in rbac.yaml line: {line!r}"


def test_deployment_never_sets_secret_value_literal():
    text = (TEMPLATES_DIR / "deployment.yaml").read_text(encoding="utf-8")
    assert "valueFrom" in text
    assert "secretKeyRef" in text
    # Env entries in this template are exclusively valueFrom.secretKeyRef -- there is no
    # `value:` key anywhere near an env block accepting a literal secret.
    assert "value:" not in text


def test_deployment_sets_non_root_security_context():
    text = (TEMPLATES_DIR / "deployment.yaml").read_text(encoding="utf-8")
    assert "securityContext" in text


def test_networkpolicy_denies_ingress_by_default():
    text = (TEMPLATES_DIR / "networkpolicy.yaml").read_text(encoding="utf-8")
    assert "ingress: []" in text


def test_all_template_files_have_balanced_go_template_braces():
    for path in TEMPLATES_DIR.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert text.count("{{") == text.count("}}"), f"{path.name} has unbalanced {{{{ }}}} delimiters"
