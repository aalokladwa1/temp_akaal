"""
tests.unit.engine_fabric.test_p7b_round3_native_identity_hostile
=====================================================================
P7B Group-1 Hostile Review Round 3 -- native cloud identity hostile review (§8-§12).

Targets two real under-validation-in-the-wrong-direction bugs found this round:
  1. AWSResourceLocator's ARN regex hardcoded the "aws" partition, rejecting genuine
     "aws-cn"/"aws-us-gov" ARNs, AND required a 12-digit account segment, rejecting
     genuine accountless global ARNs (e.g. S3 bucket ARNs).
  2. GCPBoundary's project_id validator only accepted the human-readable project ID
     form, rejecting a genuine numeric GCP project NUMBER.

Also proves the opposite direction still holds: these fixes do not create false
cross-form/cross-partition/cross-account equivalence.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.environment import EnvironmentValidationError, GCPBoundary
from akaalEngine.fabric.resource_identity import AWSResourceLocator, ResourceLocatorValidationError


def test_aws_cn_partition_arn_accepted():
    locator = AWSResourceLocator(arn="arn:aws-cn:s3:cn-north-1:123456789012:bucket/mybucket", account_id="123456789012")
    assert locator.arn.startswith("arn:aws-cn:")


def test_aws_us_gov_partition_arn_accepted():
    locator = AWSResourceLocator(arn="arn:aws-us-gov:s3:us-gov-west-1:123456789012:bucket/mybucket", account_id="123456789012")
    assert locator.arn.startswith("arn:aws-us-gov:")


def test_accountless_global_s3_arn_accepted():
    """S3 bucket ARNs genuinely have no account segment -- must not be rejected."""
    locator = AWSResourceLocator(arn="arn:aws:s3:::my-global-bucket", account_id="123456789012")
    assert locator.native_identifier() == "arn:aws:s3:::my-global-bucket"


def test_arn_still_rejects_completely_malformed_input():
    """The fix must not become so permissive that garbage is accepted."""
    with pytest.raises(ResourceLocatorValidationError):
        AWSResourceLocator(arn="not-an-arn-at-all", account_id="123456789012")
    with pytest.raises(ResourceLocatorValidationError):
        AWSResourceLocator(arn="arn:notaws:s3:::bucket", account_id="123456789012")


def test_arn_with_account_still_enforces_account_match():
    """The relaxation for accountless ARNs must not weaken the case where an account
    segment IS present -- cross-account mismatch is still caught."""
    with pytest.raises(ResourceLocatorValidationError):
        AWSResourceLocator(arn="arn:aws:iam::999999999999:role/x", account_id="123456789012")


def test_gcp_project_number_accepted():
    boundary = GCPBoundary(project_id="123456789012")
    assert boundary.project_id == "123456789012"


def test_gcp_project_id_still_accepted():
    boundary = GCPBoundary(project_id="my-real-project-1")
    assert boundary.project_id == "my-real-project-1"


def test_gcp_project_id_and_number_are_not_silently_equivalent():
    """Registering under the ID form and the number form for what a human knows to be
    the 'same' project must be treated as two DIFFERENT physical boundaries -- this
    module has no authoritative way to know they're the same project, and must not
    guess. (This is a deliberate, disclosed limitation -- true ID<->number resolution
    requires a live GCP Resource Manager call, which is EXTERNAL_DEFERRED.)"""
    by_id = GCPBoundary(project_id="my-real-project-1")
    by_number = GCPBoundary(project_id="123456789012")
    assert by_id.native_key() != by_number.native_key()


def test_gcp_boundary_rejects_garbage():
    with pytest.raises(EnvironmentValidationError):
        GCPBoundary(project_id="")
    with pytest.raises(EnvironmentValidationError):
        GCPBoundary(project_id="UPPERCASE-NOT-ALLOWED")
    with pytest.raises(EnvironmentValidationError):
        GCPBoundary(project_id="ab")  # too short for the ID form, not all-digit either
