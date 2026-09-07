"""
tests.unit.engine_fabric.test_p7b_round6_azure_native_identity_hostile
===========================================================================
P7B Group-1 Hostile Closure Round 6 -- Azure native-resource identity hostile matrix
(blocker #1). Covers casing, nested resources, provider namespace, malformed IDs,
subscription/resource-group mismatch, cross-subscription confusion.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.environment import AzureBoundary, EnvironmentValidationError
from akaalEngine.fabric.resource_identity import AzureResourceLocator, ResourceLocatorValidationError


# ---------------------------------------------------------------------------
# Casing
# ---------------------------------------------------------------------------

def test_azure_resource_id_with_different_subscription_guid_casing_still_recognized_as_same_subscription():
    """Azure subscription GUIDs are hex and genuinely case-insensitive -- a resource_id
    returned with a differently-cased GUID than the caller's own subscription_id string
    must still be recognized as the SAME subscription, not falsely rejected as a
    mismatch (over-validation)."""
    locator = AzureResourceLocator(
        resource_id="/subscriptions/ABCDEF12-1111-2222-3333-444444444444/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/acct1",
        subscription_id="abcdef12-1111-2222-3333-444444444444",  # lowercase, same GUID
    )
    assert locator.subscription_id.lower() == "abcdef12-1111-2222-3333-444444444444"


def test_azure_resource_id_path_keyword_casing_variants_accepted():
    """Azure Resource Manager treats the path keywords (subscriptions/resourceGroups/
    providers) case-insensitively -- a resource ID returned with different keyword
    casing by an older API/CLI version must not be rejected as malformed."""
    variant = AzureResourceLocator(
        resource_id="/SUBSCRIPTIONS/11111111-1111-1111-1111-111111111111/resourcegroups/rg1/PROVIDERS/Microsoft.Storage/storageAccounts/acct1",
        subscription_id="11111111-1111-1111-1111-111111111111",
    )
    assert variant.subscription_id == "11111111-1111-1111-1111-111111111111"


def test_azure_resource_id_casing_never_creates_cross_subscription_equivalence():
    """The casing fix must not become so permissive that TWO GENUINELY DIFFERENT
    subscription GUIDs (differing in more than casing) are treated as equal."""
    with pytest.raises(ResourceLocatorValidationError):
        AzureResourceLocator(
            resource_id="/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/acct1",
            subscription_id="22222222-2222-2222-2222-222222222222",  # genuinely different GUID
        )


# ---------------------------------------------------------------------------
# Nested resources / provider namespace
# ---------------------------------------------------------------------------

def test_azure_deeply_nested_child_resource_id_accepted():
    """A genuine nested/child resource (e.g. a SQL database under a SQL server, or a
    subnet under a VNet) has MORE path segments than a top-level resource -- must not be
    rejected merely for depth."""
    locator = AzureResourceLocator(
        resource_id="/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg1/providers/Microsoft.Sql/servers/srv1/databases/db1",
        subscription_id="11111111-1111-1111-1111-111111111111",
    )
    assert "databases/db1" in locator.resource_id


def test_azure_deeply_nested_grandchild_resource_id_accepted():
    """Subnet under VNet under network resource group -- three levels of nesting."""
    locator = AzureResourceLocator(
        resource_id="/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-net/providers/Microsoft.Network/virtualNetworks/vnet1/subnets/subnet1",
        subscription_id="11111111-1111-1111-1111-111111111111",
    )
    assert "subnets/subnet1" in locator.resource_id


def test_azure_provider_namespace_with_multiple_dots_accepted():
    """Real Azure provider namespaces can contain multiple dot-separated segments
    (e.g. Microsoft.DocumentDB, Microsoft.ContainerService) -- must not be rejected."""
    locator = AzureResourceLocator(
        resource_id="/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg1/providers/Microsoft.DocumentDB/databaseAccounts/acct1",
        subscription_id="11111111-1111-1111-1111-111111111111",
    )
    assert "Microsoft.DocumentDB" in locator.resource_id


# ---------------------------------------------------------------------------
# Malformed IDs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("malformed_id", [
    "not-a-resource-id-at-all",
    "/subscriptions/not-a-guid/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/acct1",
    "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups//providers/Microsoft.Storage/storageAccounts/acct1",
    "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg1",  # missing providers segment entirely
    "",
    "/subscriptions/11111111-1111-1111-1111-111111111111",
])
def test_azure_malformed_resource_ids_rejected(malformed_id):
    with pytest.raises(ResourceLocatorValidationError):
        AzureResourceLocator(resource_id=malformed_id, subscription_id="11111111-1111-1111-1111-111111111111")


# ---------------------------------------------------------------------------
# Subscription / resource-group mismatch, cross-subscription confusion
# ---------------------------------------------------------------------------

def test_azure_resource_group_typo_does_not_silently_match_a_different_resource_group():
    """Two resources in DIFFERENT resource groups under the same subscription must
    remain genuinely distinct locators -- no accidental equivalence."""
    rg1 = AzureResourceLocator(
        resource_id="/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/production-rg/providers/Microsoft.Storage/storageAccounts/acct1",
        subscription_id="11111111-1111-1111-1111-111111111111",
    )
    rg2 = AzureResourceLocator(
        resource_id="/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/staging-rg/providers/Microsoft.Storage/storageAccounts/acct1",
        subscription_id="11111111-1111-1111-1111-111111111111",
    )
    assert rg1.resource_id != rg2.resource_id
    assert rg1.native_identifier() != rg2.native_identifier()


def test_azure_subscription_guid_appearing_in_resource_group_name_does_not_grant_false_match():
    """CRITICAL: a resource GENUINELY in subscription B, whose resource-group name
    happens to contain subscription A's GUID as literal text (e.g. crafted as
    'rg-<A-guid>-evil'), must NOT validate against a locator declaring subscription A.
    A blanket substring search anywhere in the resource_id string is a real
    cross-subscription vulnerability; only the ACTUAL subscription path segment may be
    compared."""
    with pytest.raises(ResourceLocatorValidationError):
        AzureResourceLocator(
            resource_id=(
                "/subscriptions/99999999-9999-9999-9999-999999999999/resourceGroups/"
                "rg-11111111-1111-1111-1111-111111111111-evil/providers/Microsoft.Storage/storageAccounts/x"
            ),
            subscription_id="11111111-1111-1111-1111-111111111111",
        )


def test_azure_cross_subscription_locator_construction_rejected():
    """An attacker-crafted resource_id naming subscription B while the caller declares
    subscription A must be rejected at construction, not silently accepted."""
    with pytest.raises(ResourceLocatorValidationError):
        AzureResourceLocator(
            resource_id="/subscriptions/99999999-9999-9999-9999-999999999999/resourceGroups/victim-rg/providers/Microsoft.Storage/storageAccounts/stolen",
            subscription_id="11111111-1111-1111-1111-111111111111",
        )


def test_azure_tenant_vs_subscription_confusion_environment_boundary():
    """AzureBoundary's tenant_id and subscription_id are genuinely different Azure
    concepts (Entra tenant vs. billing/resource subscription) -- a caller must not be
    able to construct a boundary that conflates them (e.g. passing the same GUID for
    both is legal -- a subscription CAN belong to a tenant with a coincidentally
    logged value -- but the fields themselves must remain independently validated and
    never silently defaulted from one another)."""
    boundary = AzureBoundary(subscription_id="11111111-1111-1111-1111-111111111111", tenant_id="22222222-2222-2222-2222-222222222222")
    assert boundary.subscription_id != boundary.tenant_id
    assert boundary.native_key() == ("AZURE", "11111111-1111-1111-1111-111111111111")  # native_key is subscription-scoped, never tenant-scoped


def test_azure_boundary_invalid_tenant_id_format_rejected():
    with pytest.raises(EnvironmentValidationError):
        AzureBoundary(subscription_id="11111111-1111-1111-1111-111111111111", tenant_id="not-a-guid")


def test_azure_two_subscriptions_under_the_same_tenant_remain_distinct_environments():
    """A shared Entra tenant does not collapse two subscriptions into one environment
    boundary -- native_key is subscription-scoped."""
    sub_a = AzureBoundary(subscription_id="11111111-1111-1111-1111-111111111111", tenant_id="99999999-9999-9999-9999-999999999999")
    sub_b = AzureBoundary(subscription_id="22222222-2222-2222-2222-222222222222", tenant_id="99999999-9999-9999-9999-999999999999")
    assert sub_a.native_key() != sub_b.native_key()
