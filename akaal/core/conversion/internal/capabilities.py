"""
Akaal — Capability Matrices & Provider
======================================
Defines database capability structures and provides logic for capabilities negotiation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple
from akaal.core.conversion.api.models import DbVersion, DataType
from akaal.core.models.enums import SystemType

class CapabilityType(str, Enum):
    JSON = "JSON"
    UUID = "UUID"
    IDENTITY = "IDENTITY"
    GENERATED_COLUMNS = "GENERATED_COLUMNS"
    SPATIAL = "SPATIAL"
    XML = "XML"
    ARRAYS = "ARRAYS"
    ENUM = "ENUM"
    DOMAINS = "DOMAINS"
    UDT = "UDT"
    NETWORK = "NETWORK"
    MONEY = "MONEY"
    RANGE = "RANGE"
    COMPOSITE = "COMPOSITE"
    BOOLEAN = "BOOLEAN"
    TIMEZONE = "TIMEZONE"


class NegotiationLevel(str, Enum):
    NATIVE = "NATIVE"
    EMULATED = "EMULATED"
    PLUGIN_PROVIDED = "PLUGIN_PROVIDED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class EmulationSpec:
    emulated_target_type: str
    check_constraints: Tuple[str, ...] = field(default_factory=tuple)
    transform_hooks: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VendorCapability:
    capability_type: CapabilityType
    supported: bool
    native_type_name: Optional[str] = None
    max_precision: Optional[int] = None
    max_scale: Optional[int] = None
    max_length: Optional[int] = None
    emulation: Optional[EmulationSpec] = None


@dataclass(frozen=True)
class CapabilityMatrix:
    matrix_version: str
    vendor: str
    min_version: DbVersion
    max_version: DbVersion
    capabilities: Dict[CapabilityType, VendorCapability]


class ICapabilityProvider(ABC):
    """Interface for obtaining vendor capability matrices based on system type and version."""

    @abstractmethod
    def get_matrix(self, vendor: str, version: DbVersion) -> Optional[CapabilityMatrix]:
        """Retrieves the capability matrix matching the vendor and version."""
        pass


class DefaultCapabilityProvider(ICapabilityProvider):
    """Default implementation of ICapabilityProvider with pre-defined matrices for core databases."""

    def __init__(self):
        self._matrices: Dict[str, Tuple[CapabilityMatrix, ...]] = {}
        self._initialize_core_matrices()

    def get_matrix(self, vendor: str, version: DbVersion) -> Optional[CapabilityMatrix]:
        vendor_normalized = self._normalize_vendor(vendor)
        
        # Block invalid or empty version objects
        if version.major == 0 and version.minor == 0 and version.patch == 0:
            # Capabilities default to blocked if version is not recognized.
            blocked_caps = {
                cap_type: VendorCapability(cap_type, supported=False)
                for cap_type in CapabilityType
            }
            return CapabilityMatrix(
                matrix_version="1.0.0",
                vendor=vendor_normalized,
                min_version=version,
                max_version=version,
                capabilities=blocked_caps
            )

        matrices = self._matrices.get(vendor_normalized, ())
        for matrix in matrices:
            if matrix.min_version <= version <= matrix.max_version:
                return matrix

        # Unknown-version behavior: default capabilities to blocked
        blocked_caps = {
            cap_type: VendorCapability(cap_type, supported=False)
            for cap_type in CapabilityType
        }
        return CapabilityMatrix(
            matrix_version="1.0.0",
            vendor=vendor_normalized,
            min_version=version,
            max_version=version,
            capabilities=blocked_caps
        )

    def register_matrix(self, matrix: CapabilityMatrix) -> None:
        vendor_normalized = self._normalize_vendor(matrix.vendor)
        if vendor_normalized not in self._matrices:
            self._matrices[vendor_normalized] = ()
        self._matrices[vendor_normalized] = self._matrices[vendor_normalized] + (matrix,)

    def _normalize_vendor(self, vendor: str) -> str:
        v = vendor.upper().strip()
        if v in ("MSSQL", "SQLSERVER", "SQL SERVER"):
            return "MSSQL"
        return v

    def _initialize_core_matrices(self):
        # 1.1 PostgreSQL 9.x (No native identity support)
        pg_9_caps = {
            CapabilityType.BOOLEAN: VendorCapability(CapabilityType.BOOLEAN, True, "BOOLEAN"),
            CapabilityType.JSON: VendorCapability(CapabilityType.JSON, True, "JSONB"),
            CapabilityType.UUID: VendorCapability(CapabilityType.UUID, True, "UUID"),
            CapabilityType.IDENTITY: VendorCapability(CapabilityType.IDENTITY, False, None),
            CapabilityType.TIMEZONE: VendorCapability(CapabilityType.TIMEZONE, True, "TIMESTAMPTZ"),
            CapabilityType.XML: VendorCapability(CapabilityType.XML, True, "XML"),
            CapabilityType.ARRAYS: VendorCapability(CapabilityType.ARRAYS, True, "ARRAY"),
            CapabilityType.MONEY: VendorCapability(CapabilityType.MONEY, True, "MONEY"),
        }
        self.register_matrix(CapabilityMatrix(
            matrix_version="1.0.0",
            vendor="POSTGRESQL",
            min_version=DbVersion(9, 0, 0, "9.0"),
            max_version=DbVersion(9, 99, 99, "9.99"),
            capabilities=pg_9_caps
        ))

        # 1.2 PostgreSQL 10+ (Native identity support)
        pg_10_caps = pg_9_caps.copy()
        pg_10_caps[CapabilityType.IDENTITY] = VendorCapability(
            CapabilityType.IDENTITY, True, "GENERATED ALWAYS AS IDENTITY"
        )
        self.register_matrix(CapabilityMatrix(
            matrix_version="1.0.0",
            vendor="POSTGRESQL",
            min_version=DbVersion(10, 0, 0, "10.0"),
            max_version=DbVersion(99, 99, 99, "99.99"),
            capabilities=pg_10_caps
        ))

        # 2.1 MySQL (5.7)
        mysql_57_caps = {
            CapabilityType.BOOLEAN: VendorCapability(
                CapabilityType.BOOLEAN, True, None,
                emulation=EmulationSpec(emulated_target_type="TINYINT(1)")
            ),
            CapabilityType.JSON: VendorCapability(CapabilityType.JSON, True, "JSON"),
            CapabilityType.UUID: VendorCapability(
                CapabilityType.UUID, True, None,
                emulation=EmulationSpec(emulated_target_type="VARCHAR(36)")
            ),
            CapabilityType.IDENTITY: VendorCapability(CapabilityType.IDENTITY, True, "AUTO_INCREMENT"),
            CapabilityType.TIMEZONE: VendorCapability(
                CapabilityType.TIMEZONE, True, None,
                emulation=EmulationSpec(emulated_target_type="TIMESTAMP")
            ),
            CapabilityType.XML: VendorCapability(CapabilityType.XML, False, None),
            CapabilityType.ARRAYS: VendorCapability(CapabilityType.ARRAYS, False, None),
        }
        self.register_matrix(CapabilityMatrix(
            matrix_version="1.0.0",
            vendor="MYSQL",
            min_version=DbVersion(5, 7, 0, "5.7"),
            max_version=DbVersion(7, 99, 99, "7.99"),
            capabilities=mysql_57_caps
        ))

        # 2.2 MySQL (8.0+)
        mysql_80_caps = mysql_57_caps.copy()
        mysql_80_caps[CapabilityType.GENERATED_COLUMNS] = VendorCapability(
            CapabilityType.GENERATED_COLUMNS, True, "GENERATED ALWAYS AS"
        )
        self.register_matrix(CapabilityMatrix(
            matrix_version="1.0.0",
            vendor="MYSQL",
            min_version=DbVersion(8, 0, 0, "8.0"),
            max_version=DbVersion(99, 99, 99, "99.99"),
            capabilities=mysql_80_caps
        ))

        # 3.1 Oracle 11g (No native identity support)
        oracle_11_caps = {
            CapabilityType.BOOLEAN: VendorCapability(
                CapabilityType.BOOLEAN, True, None,
                emulation=EmulationSpec(
                    emulated_target_type="NUMBER(1)",
                    check_constraints=("CHECK (col IN (0, 1))",)
                )
            ),
            CapabilityType.JSON: VendorCapability(
                CapabilityType.JSON, True, None,
                emulation=EmulationSpec(
                    emulated_target_type="CLOB",
                    check_constraints=("CHECK (col IS JSON)",)
                )
            ),
            CapabilityType.UUID: VendorCapability(
                CapabilityType.UUID, True, None,
                emulation=EmulationSpec(emulated_target_type="VARCHAR2(36)")
            ),
            CapabilityType.IDENTITY: VendorCapability(CapabilityType.IDENTITY, False, None),
            CapabilityType.TIMEZONE: VendorCapability(CapabilityType.TIMEZONE, True, "TIMESTAMP WITH TIME ZONE"),
            CapabilityType.XML: VendorCapability(CapabilityType.XML, True, "XMLTYPE"),
            CapabilityType.ARRAYS: VendorCapability(CapabilityType.ARRAYS, False, None),
        }
        self.register_matrix(CapabilityMatrix(
            matrix_version="1.0.0",
            vendor="ORACLE",
            min_version=DbVersion(11, 0, 0, "11g"),
            max_version=DbVersion(11, 99, 99, "11.99"),
            capabilities=oracle_11_caps
        ))

        # 3.2 Oracle 12c+ (Native identity support)
        oracle_12_caps = oracle_11_caps.copy()
        oracle_12_caps[CapabilityType.IDENTITY] = VendorCapability(
            CapabilityType.IDENTITY, True, "GENERATED AS IDENTITY"
        )
        self.register_matrix(CapabilityMatrix(
            matrix_version="1.0.0",
            vendor="ORACLE",
            min_version=DbVersion(12, 0, 0, "12c"),
            max_version=DbVersion(99, 99, 99, "99.99"),
            capabilities=oracle_12_caps
        ))

        # 4. SQL Server (MSSQL >= 2012)
        mssql_caps = {
            CapabilityType.BOOLEAN: VendorCapability(CapabilityType.BOOLEAN, True, "BIT"),
            CapabilityType.JSON: VendorCapability(
                CapabilityType.JSON, True, None,
                emulation=EmulationSpec(
                    emulated_target_type="NVARCHAR(MAX)",
                    check_constraints=("ISJSON(col) = 1",)
                )
            ),
            CapabilityType.UUID: VendorCapability(CapabilityType.UUID, True, "UNIQUEIDENTIFIER"),
            CapabilityType.IDENTITY: VendorCapability(CapabilityType.IDENTITY, True, "IDENTITY(1,1)"),
            CapabilityType.TIMEZONE: VendorCapability(CapabilityType.TIMEZONE, True, "DATETIMEOFFSET"),
            CapabilityType.XML: VendorCapability(CapabilityType.XML, True, "XML"),
            CapabilityType.ARRAYS: VendorCapability(CapabilityType.ARRAYS, False, None),
        }
        self.register_matrix(CapabilityMatrix(
            matrix_version="1.0.0",
            vendor="MSSQL",
            min_version=DbVersion(11, 0, 0, "2012"),
            max_version=DbVersion(99, 99, 99, "99.99"),
            capabilities=mssql_caps
        ))
