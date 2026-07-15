from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class ValidationConfiguration:
    strict_naming: bool = True
    pk_required: bool = True
    index_limit: int = 5
    allow_precision_loss: bool = False
    custom_rules: Tuple[str, ...] = field(default_factory=tuple)
