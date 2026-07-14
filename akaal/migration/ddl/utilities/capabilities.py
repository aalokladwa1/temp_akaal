from dataclasses import dataclass

@dataclass(frozen=True)
class DialectCapabilities:
    """
    Data model defining the features and syntax structures supported by
    a target database management system dialect.
    """
    supports_transactional_ddl: bool = True
    supports_if_exists: bool = True
    supports_if_not_exists: bool = True
    supports_concurrent_indexes: bool = False
    supports_sequence_increment: bool = True
    requires_index_table_on_drop: bool = False
