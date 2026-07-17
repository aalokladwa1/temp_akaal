"""
Akaal — Identity Migration Progression Algorithms
==================================================
Provides deterministic index-based safe-next value resolution and state normalization.
"""

import math
from typing import Optional, List
from akaal.migration.models.identity import IdentityRuntimeState, GeneratorValueSemantics


class IdentityOverflowError(ValueError):
    """Raised when sequence progression exceeds the maximum limit or underflows the minimum limit."""
    pass


class CycleCollisionError(ValueError):
    """Raised when a cycling generator collides with existing keys in the target table."""
    pass


class IdentityProgressionEngine:
    """
    Mathematical engine implementing state normalization, safe-next index resolution,
    and bounds check formulas.
    """

    @staticmethod
    def align_value(x: int, start: int, increment: int) -> int:
        """
        Aligns a value x to the progression V(p) = start + p * increment.
        Rounds down (for I > 0) or up (for I < 0) to find the nearest valid index p.
        """
        if increment == 0:
            raise ValueError("Sequence increment cannot be zero.")
        p = math.floor((x - start) / increment)
        return start + p * increment

    @staticmethod
    def resolve_safe_next(
        start: int,
        increment: int,
        min_value: int,
        max_value: int,
        cycle: bool,
        table_max: Optional[int] = None,
        table_min: Optional[int] = None,
        source_state: Optional[IdentityRuntimeState] = None,
        target_state: Optional[IdentityRuntimeState] = None,
        existing_keys: Optional[List[int]] = None
    ) -> int:
        """
        Calculates the safe next value (V_emit) strictly above (for I > 0) or below (for I < 0)
        table states and generator states.
        
        Equation: V(p) = start + p * increment
        Index: p = max(p_mat, p_src, p_tgt)
        """
        if increment == 0:
            raise ValueError("Sequence increment cannot be zero.")

        # 1. Calculate materialized progression index (p_mat)
        if increment > 0:
            if table_max is None or table_max < start:
                p_mat = 0
            else:
                p_mat = max(0, math.floor((table_max - start) / increment) + 1)
        else:
            if table_min is None or table_min > start:
                p_mat = 0
            else:
                p_mat = max(0, math.floor((table_min - start) / increment) + 1)

        # 2. Map source state progression index (p_src)
        p_src = 0
        if source_state and source_state.current_generator_value is not None:
            c_val = source_state.current_generator_value
            sem = source_state.value_semantics
            
            if sem in (GeneratorValueSemantics.LAST_EMITTED, GeneratorValueSemantics.STORED_COUNTER):
                p_src = max(0, math.floor((c_val - start) / increment) + 1)
            elif sem in (GeneratorValueSemantics.NEXT_TO_EMIT, GeneratorValueSemantics.TABLE_NEXT_VALUE):
                p_src = max(0, math.ceil((c_val - start) / increment))

        # 3. Map target state progression index (p_tgt)
        p_tgt = 0
        if target_state and target_state.current_generator_value is not None:
            c_val = target_state.current_generator_value
            sem = target_state.value_semantics
            
            if sem in (GeneratorValueSemantics.LAST_EMITTED, GeneratorValueSemantics.STORED_COUNTER):
                p_tgt = max(0, math.floor((c_val - start) / increment) + 1)
            elif sem in (GeneratorValueSemantics.NEXT_TO_EMIT, GeneratorValueSemantics.TABLE_NEXT_VALUE):
                p_tgt = max(0, math.ceil((c_val - start) / increment))

        # 4. Select safe index
        p_next = max(p_mat, p_src, p_tgt)

        # 5. Compute value: V_emit = start + p_next * increment
        v_emit = start + p_next * increment

        # 6. Bounds and cycle checks
        if increment > 0:
            if v_emit > max_value:
                if cycle:
                    # Cycling generator: wrap to min_value
                    range_size = max_value - min_value + 1
                    wrapped_val = min_value + ((v_emit - min_value) % range_size)
                    
                    # Cycle collision check
                    if existing_keys and wrapped_val in existing_keys:
                        raise CycleCollisionError(f"Cycling value {wrapped_val} collides with existing keys.")
                    return wrapped_val
                else:
                    raise IdentityOverflowError(f"Sequence emission value {v_emit} overflows max_value {max_value}.")
            if v_emit < min_value:
                raise IdentityOverflowError(f"Sequence emission value {v_emit} underflows min_value {min_value}.")
        else: # increment < 0
            if v_emit < min_value:
                if cycle:
                    # Cycling generator: wrap to max_value
                    range_size = max_value - min_value + 1
                    wrapped_val = max_value - ((min_value - v_emit) % range_size)
                    
                    # Cycle collision check
                    if existing_keys and wrapped_val in existing_keys:
                        raise CycleCollisionError(f"Cycling value {wrapped_val} collides with existing keys.")
                    return wrapped_val
                else:
                    raise IdentityOverflowError(f"Sequence emission value {v_emit} underflows min_value {min_value}.")
            if v_emit > max_value:
                raise IdentityOverflowError(f"Sequence emission value {v_emit} overflows max_value {max_value}.")

        return v_emit
