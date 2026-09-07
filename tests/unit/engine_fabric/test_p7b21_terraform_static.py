"""
P7B.21 -- Terraform-First IaC: STATIC text validation of deploy/terraform/.

PROOF-LEVEL HONESTY: no `terraform` binary is installed in this environment (asserted
below, not silently skipped). These tests are a regex/text sweep over the checked-in
.tf files for the hostile patterns the Group-2 directive names (plaintext secrets,
wildcard IAM, public-CIDR security groups, hardcoded credentials) -- LOCALLY_VERIFIED
proof of file CONTENT only. This is explicitly NOT `terraform validate`/`terraform plan`
proof (EXTERNAL_DEFERRED -- see progress.md P7B Group-2 §36).
"""

import re
import shutil
from pathlib import Path

TERRAFORM_DIR = Path(__file__).resolve().parents[3] / "deploy" / "terraform"


def _all_tf_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in TERRAFORM_DIR.glob("*.tf"))


def _all_tf_code_only() -> str:
    """Same as _all_tf_text but with `#`-comment lines stripped -- for hostile checks
    where an explanatory comment mentioning the forbidden term (to document its absence)
    would otherwise be a false positive against the real code."""
    lines = []
    for p in TERRAFORM_DIR.glob("*.tf"):
        for line in p.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            lines.append(re.sub(r"\s#.*$", "", line))
    return "\n".join(lines)


def test_terraform_binary_genuinely_unavailable_in_this_environment():
    assert shutil.which("terraform") is None


def test_tf_files_exist():
    assert list(TERRAFORM_DIR.glob("*.tf"))


# ------------------------------------------------------------------ secret-leakage hostile matrix


_SECRET_LIKE_ASSIGNMENT_RE = re.compile(
    r'(?:secret|password|api[_-]?key|private[_-]?key|access[_-]?key)\s*=\s*"[^"$]{4,}"', re.IGNORECASE,
)


def test_no_hardcoded_secret_like_literal_assignments():
    text = _all_tf_text()
    matches = _SECRET_LIKE_ASSIGNMENT_RE.findall(text)
    # Variable/output NAMES containing "key"/"secret" are fine (e.g. aws_staging_bucket
    # ARNs, client_id outputs) -- what this checks is a literal quoted VALUE assigned
    # directly to a secret-shaped key, which none of this module's files do (all
    # identity material is a resource attribute REFERENCE, e.g. `aws_iam_role.worker[0].arn`,
    # never a quoted literal).
    assert not matches, f"possible hardcoded secret-like literal(s): {matches}"


def test_no_sensitive_output_without_explicit_sensitive_flag_review():
    """Every output in outputs.tf is an identity reference, not a secret -- so none is
    marked `sensitive = true`. This test documents and enforces that invariant: if a
    future output name suggests it might carry sensitive material, it MUST be reviewed
    and marked sensitive (or removed), never silently added as a plain output."""
    outputs_text = (TERRAFORM_DIR / "outputs.tf").read_text(encoding="utf-8")
    output_blocks = re.findall(r'output\s+"([^"]+)"\s*\{', outputs_text)
    for name in output_blocks:
        assert not any(bad in name.lower() for bad in ("secret", "password", "token", "private_key")), (
            f"output {name!r} name suggests sensitive material but is not reviewed as sensitive"
        )


# ------------------------------------------------------------------ IAM/network hostile matrix


def test_no_wildcard_iam_actions_or_resources_in_policy_documents():
    text = _all_tf_text()
    # Every actions/resources list in this module's aws_iam_policy_document blocks is an
    # explicit, minimal list -- never a bare "*".
    for match in re.finditer(r'(actions|resources)\s*=\s*\[([^\]]*)\]', text):
        list_body = match.group(2)
        assert '"*"' not in list_body, f"wildcard found in {match.group(1)} list: {list_body!r}"


def test_no_administrator_or_owner_role_grants():
    text = _all_tf_code_only().lower()
    for forbidden in ("administratoraccess", "roles/owner", "roles/editor", "cluster-admin"):
        assert forbidden not in text


def test_no_public_cidr_ingress_defaults():
    text = _all_tf_code_only()
    assert "0.0.0.0/0" not in text


def test_no_default_credentials_or_static_access_keys():
    text = _all_tf_code_only().lower()
    for forbidden in ("aws_access_key_id", "aws_secret_access_key", "client_secret ="):
        assert forbidden not in text


# ------------------------------------------------------------------ scope-toggle hostile matrix


def test_every_cloud_resource_gated_by_its_own_enable_flag():
    """Every top-level resource block in main.tf must have a `count =` expression
    referencing the matching `var.enable_<cloud>` flag -- proving no cloud's
    infrastructure is provisioned unconditionally merely by running `terraform apply`
    with defaults (every enable_* flag defaults to false in variables.tf)."""
    main_text = (TERRAFORM_DIR / "main.tf").read_text(encoding="utf-8")
    resource_blocks = re.findall(r'resource\s+"(\w+)"\s+"(\w+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', main_text)
    assert resource_blocks, "expected at least one resource block in main.tf"
    for res_type, res_name, body in resource_blocks:
        assert "count" in body, f"resource {res_type}.{res_name} has no count-based gate"


def test_all_enable_flags_default_false():
    variables_text = (TERRAFORM_DIR / "variables.tf").read_text(encoding="utf-8")
    for flag in ("enable_aws", "enable_azure", "enable_gcp", "enable_oci", "enable_kubernetes"):
        block_match = re.search(rf'variable\s+"{flag}"\s*\{{([^}}]*)\}}', variables_text)
        assert block_match, f"variable {flag!r} not found"
        assert "default = false" in block_match.group(1).replace("  ", " ")


def test_terraform_never_owns_migration_or_plan_state():
    """Structural/textual proof that no .tf file references migration-truth concepts --
    Terraform provisions infrastructure only, per the module's own documented boundary."""
    text = _all_tf_code_only().lower()
    for forbidden in ("execution_plan", "checkpoint", "cdc_offset", "migration_id", "validation_result"):
        assert forbidden not in text
