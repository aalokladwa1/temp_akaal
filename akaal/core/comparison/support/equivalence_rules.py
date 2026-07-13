"""
Akaal — Equivalence Rules
=========================
Houses custom logic for comparing database defaults and type mapping equivalences.
"""

from akaal.core.comparison.models.context import ComparisonContext


def are_types_equivalent(
    exp_type: str,
    act_type: str,
    exp_raw: str,
    act_raw: str,
    context: ComparisonContext,
) -> bool:
    """
    Evaluates if two data types are equivalent, factoring in ComparisonContext.
    """
    if exp_type == act_type:
        if context.strict_length_precision:
            return exp_raw.upper().strip() == act_raw.upper().strip()
        return True

    # Check custom type equivalences registry
    if context.custom_type_equivalences:
        if context.custom_type_equivalences.get(exp_type) == act_type:
            return True
        if context.custom_type_equivalences.get(act_type) == exp_type:
            return True

    return False


def are_defaults_equivalent(
    exp_default: str,
    act_default: str,
    exp_type: str,
    act_type: str,
    is_pk: bool,
) -> bool:
    """
    Checks if two normalized defaults are structurally equivalent across vendor dialects.
    
    Rule:
      MySQL PK columns with auto-increment report default value 'NULL'.
      PostgreSQL PK columns using SERIAL report default value 'NEXTVAL'.
      These are equivalent if both columns are integers and members of the primary key.
    """
    if exp_default == act_default:
        return True

    # MySQL (NULL default) -> PostgreSQL (NEXTVAL sequence) auto-increment equivalence
    if (
        is_pk
        and exp_type == "INTEGER"
        and act_type == "INTEGER"
        and exp_default == "NULL"
        and act_default == "NEXTVAL"
    ):
        return True

    return False
