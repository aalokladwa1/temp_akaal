"""
Akaal — Schema Validator
========================
Validates that incoming Schema instances are structurally valid and consistent
before the comparison engine runs.
"""

from typing import Set
from akaal.core.comparison.models import Schema, InvalidSchemaError


class SchemaValidator:
    """
    Validates structural integrity and reference constraints of schema definitions.
    Raises InvalidSchemaError if any anomalies are found.
    """

    def validate(self, schema: Schema) -> None:
        """
        Performs static validation of the Schema model structure.
        """
        if not schema:
            raise InvalidSchemaError("Schema cannot be None.")

        # 1. Casing-insensitive check for duplicate table names
        table_names_seen: Set[str] = set()
        for table in schema.tables:
            if not table.name or not table.name.strip():
                raise InvalidSchemaError("Table name cannot be empty.")
            
            norm_name = table.name.lower().strip()
            if norm_name in table_names_seen:
                raise InvalidSchemaError(f"Duplicate table definition detected: '{table.name}'.")
            table_names_seen.add(norm_name)

            # 2. Check duplicate column names & validate attributes
            col_names_seen: Set[str] = set()
            for col in table.columns:
                if not col.name or not col.name.strip():
                    raise InvalidSchemaError(f"Empty column name found on table '{table.name}'.")
                norm_col = col.name.lower().strip()
                if norm_col in col_names_seen:
                    raise InvalidSchemaError(f"Duplicate column definition '{col.name}' on table '{table.name}'.")
                col_names_seen.add(norm_col)

                if not col.data_type or not col.data_type.strip():
                    raise InvalidSchemaError(f"Empty data type for column '{col.name}' on table '{table.name}'.")

            # 3. Verify Primary Key columns exist
            if table.primary_key:
                if not table.primary_key.columns:
                    raise InvalidSchemaError(f"Primary key definition on table '{table.name}' has no columns.")
                for pk_col in table.primary_key.columns:
                    if pk_col.lower().strip() not in col_names_seen:
                        raise InvalidSchemaError(
                            f"Primary key column '{pk_col}' does not exist on table '{table.name}'."
                        )

            # 4. Verify Duplicate Indexes & Index Columns
            index_names_seen: Set[str] = set()
            for idx in table.indexes:
                if not idx.name or not idx.name.strip():
                    raise InvalidSchemaError(f"Index name on table '{table.name}' cannot be empty.")
                norm_idx = idx.name.lower().strip()
                if norm_idx in index_names_seen:
                    raise InvalidSchemaError(f"Duplicate index definition '{idx.name}' on table '{table.name}'.")
                index_names_seen.add(norm_idx)

                if not idx.columns:
                    raise InvalidSchemaError(f"Index '{idx.name}' on table '{table.name}' has no columns.")
                for idx_col in idx.columns:
                    if idx_col.lower().strip() not in col_names_seen:
                        raise InvalidSchemaError(
                            f"Index '{idx.name}' on table '{table.name}' references non-existent column '{idx_col}'."
                        )

            # 5. Verify Duplicate Constraints
            constraint_names_seen: Set[str] = set()
            for const in table.constraints:
                if const.name:
                    norm_const = const.name.lower().strip()
                    if norm_const in constraint_names_seen:
                        raise InvalidSchemaError(
                            f"Duplicate constraint definition '{const.name}' on table '{table.name}'."
                        )
                    constraint_names_seen.add(norm_const)

                if const.type == "UNIQUE":
                    if not const.columns:
                        raise InvalidSchemaError(f"Unique constraint '{const.name}' on table '{table.name}' has no columns.")
                    for const_col in const.columns:
                        if const_col.lower().strip() not in col_names_seen:
                            raise InvalidSchemaError(
                                f"Unique constraint '{const.name}' on table '{table.name}' references non-existent column '{const_col}'."
                            )

        # 6. Verify Foreign Key target references
        for table in schema.tables:
            table_cols = {col.name.lower().strip() for col in table.columns}
            for fk in table.foreign_keys:
                if not fk.name or not fk.name.strip():
                    raise InvalidSchemaError(f"Foreign key name on table '{table.name}' cannot be empty.")
                if not fk.from_columns or not fk.to_columns:
                    raise InvalidSchemaError(f"Foreign key '{fk.name}' on table '{table.name}' has empty columns list.")
                if len(fk.from_columns) != len(fk.to_columns):
                    raise InvalidSchemaError(
                        f"Foreign key '{fk.name}' column count mismatch: from={len(fk.from_columns)}, to={len(fk.to_columns)}."
                    )

                # Check from columns
                for from_col in fk.from_columns:
                    if from_col.lower().strip() not in table_cols:
                        raise InvalidSchemaError(
                            f"Foreign key '{fk.name}' references non-existent local column '{from_col}' on table '{table.name}'."
                        )

                # Check target table and columns
                target_table_norm = fk.to_table.lower().strip()
                if target_table_norm not in table_names_seen:
                    raise InvalidSchemaError(
                        f"Foreign key '{fk.name}' references non-existent table '{fk.to_table}'."
                    )

                # Fetch target table schema
                target_table = next(t for t in schema.tables if t.name.lower().strip() == target_table_norm)
                target_table_cols = {col.name.lower().strip() for col in target_table.columns}

                for to_col in fk.to_columns:
                    if to_col.lower().strip() not in target_table_cols:
                        raise InvalidSchemaError(
                            f"Foreign key '{fk.name}' references non-existent target column '{to_col}' on table '{fk.to_table}'."
                        )

        # 7. Verify global constraint and index name uniqueness across the entire schema
        global_names: Set[str] = set()
        for table in schema.tables:
            if table.primary_key and table.primary_key.name:
                pk_name = table.primary_key.name.lower().strip()
                if pk_name in global_names:
                    raise InvalidSchemaError(f"Duplicate global identifier definition: '{table.primary_key.name}'")
                global_names.add(pk_name)

            for fk in table.foreign_keys:
                if fk.name:
                    fk_name = fk.name.lower().strip()
                    if fk_name in global_names:
                        raise InvalidSchemaError(f"Duplicate global identifier definition: '{fk.name}'")
                    global_names.add(fk_name)

            for idx in table.indexes:
                if idx.name:
                    idx_name = idx.name.lower().strip()
                    if idx_name in global_names:
                        raise InvalidSchemaError(f"Duplicate global identifier definition: '{idx.name}'")
                    global_names.add(idx_name)

            for const in table.constraints:
                if const.name:
                    const_name = const.name.lower().strip()
                    if const_name in global_names:
                        raise InvalidSchemaError(f"Duplicate global identifier definition: '{const.name}'")
                    global_names.add(const_name)
