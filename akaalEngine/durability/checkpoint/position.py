"""
Generalized Row & Provider Position Tracker for Authority #5 — Durability (DUR-003).
"""

from typing import Dict, Any, Optional, Tuple
from akaalEngine.durability.models.checkpoint import RowPosition, RowPositionType
from akaalEngine.durability.models.errors import InvalidResumePositionError


class RowPositionTracker:
    """Manages creation, serialization, and validation of generalized resumable positions."""

    @staticmethod
    def create_position(
        position_type: RowPositionType,
        value: Dict[str, Any],
        column_names: Tuple[str, ...] = (),
        token: Optional[str] = None
    ) -> RowPosition:
        is_stable = position_type != RowPositionType.UNSAFE_UNAVAILABLE
        return RowPosition(
            position_type=position_type,
            value=value,
            is_stable_resume_supported=is_stable,
            column_names=column_names,
            token=token
        )

    @staticmethod
    def to_dict(pos: RowPosition) -> Dict[str, Any]:
        """Serializes RowPosition to a JSON-compatible dict."""
        return {
            "position_type": pos.position_type.value,
            "value": pos.value,
            "is_stable_resume_supported": pos.is_stable_resume_supported,
            "column_names": list(pos.column_names),
            "token": pos.token,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> RowPosition:
        """Deserializes RowPosition from dict."""
        try:
            pos_type = RowPositionType(data["position_type"])
            is_stable = data.get("is_stable_resume_supported", True)
            if pos_type == RowPositionType.UNSAFE_UNAVAILABLE and is_stable:
                raise InvalidResumePositionError("Contradictory row position encoding: UNSAFE_UNAVAILABLE cannot claim is_stable_resume_supported=True.")
            return RowPosition(
                position_type=pos_type,
                value=data.get("value", {}),
                is_stable_resume_supported=is_stable if pos_type != RowPositionType.UNSAFE_UNAVAILABLE else False,
                column_names=tuple(data.get("column_names", [])),
                token=data.get("token"),
            )
        except Exception as e:
            if isinstance(e, InvalidResumePositionError):
                raise e
            raise InvalidResumePositionError(f"Failed to deserialize RowPosition: {e}")
