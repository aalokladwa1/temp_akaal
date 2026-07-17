"""
Akaal — Identity Model Mapper
==============================
Provides utility mapping functions to convert declarative comparison IdentityDefinition objects
to and from operational migration IdentityMetadata models.
"""

from typing import Optional
from akaal.core.comparison.models import IdentityDefinition, IdentityMode
from akaal.migration.models import IdentityMetadata


class IdentityModelMapper:
    """
    Utility mapper class for Feature 1 identity models.
    """

    @staticmethod
    def to_metadata(defn: Optional[IdentityDefinition]) -> Optional[IdentityMetadata]:
        """
        Maps a declarative IdentityDefinition to an operational IdentityMetadata instance.
        """
        if not defn:
            return None

        always = (defn.mode == IdentityMode.GENERATED_ALWAYS)
        generated_by_default = (defn.mode == IdentityMode.GENERATED_BY_DEFAULT)

        return IdentityMetadata(
            always=always,
            generated_by_default=generated_by_default,
            start=defn.start,
            increment=defn.increment,
            min_value=defn.min_value,
            max_value=defn.max_value,
            cycle=defn.cycle,
            cache_size=defn.cache,
            owned_sequence=None,
            sequence_name=None,
            current_value=None
        )

    @staticmethod
    def from_metadata(meta: Optional[IdentityMetadata]) -> Optional[IdentityDefinition]:
        """
        Maps an operational IdentityMetadata instance to a declarative IdentityDefinition.
        """
        if not meta:
            return None

        # Resolve mode
        if meta.always:
            mode = IdentityMode.GENERATED_ALWAYS
        elif meta.generated_by_default:
            mode = IdentityMode.GENERATED_BY_DEFAULT
        else:
            mode = IdentityMode.SERIAL_FALLBACK

        # Map policies
        explicit_policy = "BLOCKED" if meta.always else "ALLOWED"

        return IdentityDefinition(
            mode=mode,
            start=meta.start,
            increment=meta.increment,
            min_value=meta.min_value,
            max_value=meta.max_value,
            cycle=meta.cycle,
            cache=meta.cache_size,
            order=False,
            explicit_insert_policy=explicit_policy
        )
