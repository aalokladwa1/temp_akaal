"""CloudEvents v1.0 Standard Event Envelope Specification."""

from dataclasses import dataclass, field
from typing import Any, Mapping
from akaal.workflow.utils.serialization import compute_sha256, canonical_json


@dataclass(frozen=True, slots=True)
class CloudEventV1:
    """Immutable CloudEvents v1.0 specification complaint event envelope."""

    id: str
    source: str
    type: str
    subject: str
    specversion: str = "1.0"
    time: str = "2026-01-01T00:00:00Z"
    datacontenttype: str = "application/json"
    data: Mapping[str, Any] = field(default_factory=dict)
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "specversion": self.specversion,
            "id": self.id,
            "source": self.source,
            "type": self.type,
            "subject": self.subject,
            "time": self.time,
            "datacontenttype": self.datacontenttype,
            "data": dict(self.data),
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "specversion": self.specversion,
            "id": self.id,
            "source": self.source,
            "type": self.type,
            "subject": self.subject,
            "time": self.time,
            "datacontenttype": self.datacontenttype,
            "data": dict(self.data),
            "checksum": self.checksum,
        }

    def render_json(self) -> str:
        return canonical_json(self.to_dict())
