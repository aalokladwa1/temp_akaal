"""
tests.unit.engine_fabric.test_p7b_round6_aws_native_identity_hostile
=========================================================================
P7B Group-1 Hostile Closure Round 6 -- AWS native-resource identity hostile matrix,
completing the four-cloud matrix (blocker #3). AWS partition/accountless-ARN fixes were
already made in Round 3; this file consolidates and extends coverage: region mismatch,
wrong-service confusion, cross-account substring-collision (verified NOT vulnerable,
unlike the GCP/Azure defects this round found, because ARN account extraction is
positional via `.split(':')[4]`, never a substring search).
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.environment import AWSBoundary, EnvironmentValidationError
from akaalEngine.fabric.resource_identity import AWSResourceLocator, ResourceLocatorValidationError


# ---------------------------------------------------------------------------
# Cross-account substring-collision -- verify AWS's positional extraction is NOT
# vulnerable to the same class of defect found in Azure/GCP this round
# ---------------------------------------------------------------------------

def test_aws_account_id_appearing_elsewhere_in_arn_does_not_create_false_match():
    """CRITICAL regression guard: an ARN genuinely in account B, whose RESOURCE NAME
    happens to contain account A's 12-digit id as literal text, must not validate
    against a locator declaring account A. AWS ARN account extraction is positional
    (5th colon-delimited field), never a substring search -- this proves it stays that
    way."""
    with pytest.raises(ResourceLocatorValidationError):
        AWSResourceLocator(
            arn="arn:aws:s3:us-east-1:222222222222:bucket/backup-for-111111111111-evil",
            account_id="111111111111",
        )


def test_aws_correct_account_with_similar_looking_resource_name_still_accepted():
    locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:111111111111:bucket/backup-for-111111111111-legit", account_id="111111111111")
    assert locator.account_id == "111111111111"


# ---------------------------------------------------------------------------
# Region mismatch / wrong-service confusion
# ---------------------------------------------------------------------------

def test_aws_region_field_is_informational_and_never_cross_validated_against_arn_region_without_explicit_check():
    """AWSResourceLocator.region is a separate, caller-supplied field -- document actual
    behavior: it is NOT currently cross-checked against the ARN's own region segment
    (index 3). This is honestly disclosed rather than assumed to be validated."""
    # ARN says us-east-1, caller declares region="eu-west-1" -- construction succeeds
    # today because no region cross-check exists; this is a real, disclosed limitation
    # (region is informational metadata here, account is the enforced boundary).
    locator = AWSResourceLocator(arn="arn:aws:rds:us-east-1:123456789012:db:mydb", account_id="123456789012", region="eu-west-1")
    assert locator.region == "eu-west-1"
    assert "us-east-1" in locator.arn  # the ARN's own truth is preserved regardless


def test_aws_different_services_with_same_resource_name_remain_distinct_locators():
    """An S3 bucket and an RDS instance happening to share a human-chosen name string
    must never be conflated -- the full ARN (including service segment) is the identity."""
    s3_locator = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/orders", account_id="123456789012")
    rds_locator = AWSResourceLocator(arn="arn:aws:rds:us-east-1:123456789012:db:orders", account_id="123456789012")
    assert s3_locator.arn != rds_locator.arn
    assert s3_locator.native_identifier() != rds_locator.native_identifier()


# ---------------------------------------------------------------------------
# Partition confusion (Round 3 fix, reconfirmed not to create cross-partition equivalence)
# ---------------------------------------------------------------------------

def test_aws_same_account_id_in_different_partitions_remain_distinct_resources():
    """A resource in the STANDARD aws partition and a resource with the SAME account
    number in the aws-cn partition are genuinely different physical resources (China
    partition accounts are entirely separate from standard/GovCloud accounts, even when
    the 12-digit number happens to collide with a standard-partition account) -- the
    full ARN string (including partition) remains the actual identity, never collapsed."""
    standard = AWSResourceLocator(arn="arn:aws:s3:us-east-1:123456789012:bucket/x", account_id="123456789012")
    china = AWSResourceLocator(arn="arn:aws-cn:s3:cn-north-1:123456789012:bucket/x", account_id="123456789012")
    assert standard.arn != china.arn
    assert standard.native_identifier() != china.native_identifier()


# ---------------------------------------------------------------------------
# Environment boundary
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_account", ["", "12345", "1234567890123", "abcdefghijkl", "123456789012 "])
def test_aws_boundary_malformed_account_ids_rejected(bad_account):
    with pytest.raises(EnvironmentValidationError):
        AWSBoundary(account_id=bad_account)


def test_aws_boundary_two_accounts_remain_distinct_even_with_shared_org():
    """AWSBoundary has no organization concept exposed (AWS Organizations membership is
    a separate AWS construct this module does not model) -- two distinct 12-digit
    accounts are always distinct native_key() values regardless."""
    acct_a = AWSBoundary(account_id="111111111111")
    acct_b = AWSBoundary(account_id="222222222222")
    assert acct_a.native_key() != acct_b.native_key()
