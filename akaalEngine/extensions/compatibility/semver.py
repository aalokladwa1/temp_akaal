"""
akaalEngine.extensions.compatibility.semver
===========================================
Deterministic Semantic Versioning (SemVer 2.0.0) parser and comparator.
Guarantees numeric comparisons rather than lexicographic string comparisons.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple


_SEMVER_REGEX = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


@dataclass(frozen=True)
class SemVer:
    """
    Immutable SemVer 2.0.0 representation with exact numeric component comparison.
    """
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    @classmethod
    def parse(cls, version_str: str) -> SemVer:
        """Parses a SemVer string, raising ValueError if invalid."""
        if not version_str or not isinstance(version_str, str):
            raise ValueError(f"Version string must be a non-empty string, got {version_str!r}.")

        cleaned = version_str.strip().lstrip("vV")
        match = _SEMVER_REGEX.match(cleaned)
        if not match:
            # Fallback lenient 1-part or 2-part parsing (e.g. '1.0' -> '1.0.0')
            parts = cleaned.split(".")
            if len(parts) == 1 and parts[0].isdigit():
                return cls(major=int(parts[0]), minor=0, patch=0)
            elif len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                return cls(major=int(parts[0]), minor=int(parts[1]), patch=0)
            raise ValueError(f"Invalid SemVer string: '{version_str}'. Must follow SemVer 2.0.0 format (e.g. 1.2.3).")

        d = match.groupdict()
        return cls(
            major=int(d["major"]),
            minor=int(d["minor"]),
            patch=int(d["patch"]),
            prerelease=d.get("prerelease"),
            build=d.get("buildmetadata"),
        )

    def _compare_prerelease(self, other_pre: Optional[str]) -> int:
        if self.prerelease is None and other_pre is None:
            return 0
        if self.prerelease is None and other_pre is not None:
            return 1  # No prerelease has higher precedence than prerelease
        if self.prerelease is not None and other_pre is None:
            return -1
        
        # Both have prerelease
        p1_parts = (self.prerelease or "").split(".")
        p2_parts = (other_pre or "").split(".")
        for p1, p2 in zip(p1_parts, p2_parts):
            p1_num = int(p1) if p1.isdigit() else None
            p2_num = int(p2) if p2.isdigit() else None
            if p1_num is not None and p2_num is not None:
                if p1_num != p2_num:
                    return 1 if p1_num > p2_num else -1
            elif p1_num is not None and p2_num is None:
                return -1  # Numeric identifiers have lower precedence than alphanumeric
            elif p1_num is None and p2_num is not None:
                return 1
            else:
                if p1 != p2:
                    return 1 if p1 > p2 else -1

        if len(p1_parts) != len(p2_parts):
            return 1 if len(p1_parts) > len(p2_parts) else -1
        return 0

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SemVer):
            try:
                other = SemVer.parse(str(other))
            except Exception:
                return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self._compare_prerelease(other.prerelease) == 0
        )

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, SemVer):
            other = SemVer.parse(str(other))
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        return self._compare_prerelease(other.prerelease) < 0

    def __le__(self, other: Any) -> bool:
        return self < other or self == other

    def __gt__(self, other: Any) -> bool:
        return not (self <= other)

    def __ge__(self, other: Any) -> bool:
        return not (self < other)

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            s += f"-{self.prerelease}"
        if self.build:
            s += f"+{self.build}"
        return s
