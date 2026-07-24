"""
AKAAL Platform 11 — Enterprise Trust & Certification Domain Enums.
"""

from enum import Enum


class TrustGrade(str, Enum):
    GRADE_AAA = "GRADE_AAA"  # 100% Audit-Grade Certified
    GRADE_AA = "GRADE_AA"    # Certified with minor waivers
    GRADE_A = "GRADE_A"      # Conditionally Certified
    UNTRUSTED = "UNTRUSTED"  # Failed Certification Threshold


class CertificationSealStatus(str, Enum):
    VALID = "VALID"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
