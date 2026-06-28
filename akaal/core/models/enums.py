"""
Akaal — Core Enumerations
==========================
All shared enums used across every agent and component.
Expanded to support 17 database/storage types and 9 cloud platforms.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Workflow States
# ---------------------------------------------------------------------------

# NOTE: PRE_MIGRATION_ANALYSIS, RISK_SCORED, and MIGRATION_PLANNED are placeholder
# states pending the Intelligence Phase integration phase.
class WorkflowState(str, Enum):
    IDLE                     = "IDLE"
    PROJECT_CREATED          = "PROJECT_CREATED"
    PRE_MIGRATION_ANALYSIS   = "PRE_MIGRATION_ANALYSIS"   # NEW: advisory layer
    RISK_SCORED              = "RISK_SCORED"               # NEW
    MIGRATION_PLANNED        = "MIGRATION_PLANNED"         # NEW
    DISCOVERY_STARTED        = "DISCOVERY_STARTED"
    DISCOVERY_COMPLETED      = "DISCOVERY_COMPLETED"
    DISCOVERY_VALIDATED      = "DISCOVERY_VALIDATED"
    GB_LOADING               = "GB_LOADING"
    GB_LOADED                = "GB_LOADED"
    GB_VALIDATION            = "GB_VALIDATION"
    GB_VALIDATED             = "GB_VALIDATED"
    HUMAN_APPROVAL_PENDING   = "HUMAN_APPROVAL_PENDING"
    HUMAN_APPROVED           = "HUMAN_APPROVED"
    PRODUCTION_MIGRATION     = "PRODUCTION_MIGRATION"
    PRODUCTION_VALIDATION    = "PRODUCTION_VALIDATION"
    CDC_SYNCHRONIZATION      = "CDC_SYNCHRONIZATION"
    MIGRATION_COMPLETED      = "MIGRATION_COMPLETED"
    FAILED                   = "FAILED"
    RECOVERY_STARTED         = "RECOVERY_STARTED"
    CHECKPOINT_RESTORE       = "CHECKPOINT_RESTORE"
    RETRYING                 = "RETRYING"
    ESCALATED                = "ESCALATED"
    CANCELLED                = "CANCELLED"
    PAUSED                   = "PAUSED"


# ---------------------------------------------------------------------------
# Agent Status
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    IDLE        = "IDLE"
    BUSY        = "BUSY"
    FAILED      = "FAILED"
    RECOVERING  = "RECOVERING"
    OFFLINE     = "OFFLINE"
    STANDBY     = "STANDBY"
    HEALTHY     = "HEALTHY"


# ---------------------------------------------------------------------------
# Agent Types
# ---------------------------------------------------------------------------

class AgentType(str, Enum):
    MANAGER           = "MANAGER"
    SCOUT             = "SCOUT"
    VALIDATOR         = "VALIDATOR"
    LIVE_INTEL        = "LIVE_INTEL"
    GB                = "GB"
    CHECKPOINT_ENGINE = "CHECKPOINT_ENGINE"
    CDC_ENGINE        = "CDC_ENGINE"
    STANDBY           = "STANDBY"
    SYSTEM            = "SYSTEM"
    NOTICER           = "NOTICER"
    ADVISOR           = "ADVISOR"        # NEW: pre-migration advisor agent


# ---------------------------------------------------------------------------
# Task Types
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    DISCOVERY             = "DISCOVERY"
    VALIDATION            = "VALIDATION"
    GB_IMPORT             = "GB_IMPORT"
    GB_VALIDATION         = "GB_VALIDATION"
    MIGRATION_BATCH       = "MIGRATION_BATCH"
    CDC_SYNC              = "CDC_SYNC"
    CHECKPOINT_CREATE     = "CHECKPOINT_CREATE"
    CHECKPOINT_RESTORE    = "CHECKPOINT_RESTORE"
    HEALTH_CHECK          = "HEALTH_CHECK"
    REPORT_GENERATE       = "REPORT_GENERATE"
    RECOVERY              = "RECOVERY"
    PRE_MIGRATION_ANALYSIS = "PRE_MIGRATION_ANALYSIS"   # NEW


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------

class Priority(int, Enum):
    P0_SYSTEM_CRITICAL   = 0
    P1_MIGRATION         = 1
    P2_VALIDATION        = 2
    P3_DISCOVERY         = 3
    P4_OPTIMIZATION      = 4
    P5_BACKGROUND        = 5


# ---------------------------------------------------------------------------
# Failure Types
# ---------------------------------------------------------------------------

class FailureType(str, Enum):
    MINOR    = "MINOR"
    MODERATE = "MODERATE"
    CRITICAL = "CRITICAL"
    SYSTEM   = "SYSTEM"
    UNKNOWN  = "UNKNOWN"


class FailureReason(str, Enum):
    CONNECTION_LOST        = "CONNECTION_LOST"
    PERMISSIONS_REVOKED    = "PERMISSIONS_REVOKED"
    METADATA_UNREADABLE    = "METADATA_UNREADABLE"
    SCHEMA_CORRUPTED       = "SCHEMA_CORRUPTED"
    CHECKSUM_MISMATCH      = "CHECKSUM_MISMATCH"
    VALIDATION_FAILED      = "VALIDATION_FAILED"
    AGENT_TIMEOUT          = "AGENT_TIMEOUT"
    AUTHENTICATION_FAILED  = "AUTHENTICATION_FAILED"
    INFRASTRUCTURE_ERROR   = "INFRASTRUCTURE_ERROR"
    ADAPTER_FAILURE        = "ADAPTER_FAILURE"
    DUPLICATE_REQUEST      = "DUPLICATE_REQUEST"
    UNAUTHORIZED_REQUEST   = "UNAUTHORIZED_REQUEST"
    LOOP_LIMIT_EXCEEDED    = "LOOP_LIMIT_EXCEEDED"
    UNSUPPORTED_DB_TYPE    = "UNSUPPORTED_DB_TYPE"
    UNKNOWN                = "UNKNOWN"


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------

class ApprovalDecision(str, Enum):
    APPROVE               = "APPROVE"
    REJECT                = "REJECT"
    PAUSE                 = "PAUSE"
    REQUEST_INVESTIGATION = "REQUEST_INVESTIGATION"
    CANCEL                = "CANCEL"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationResult(str, Enum):
    PASS    = "PASS"
    FAIL    = "FAIL"
    PARTIAL = "PARTIAL"
    SKIPPED = "SKIPPED"


# ---------------------------------------------------------------------------
# Migration Strategy
# ---------------------------------------------------------------------------

class MigrationStrategy(str, Enum):
    BIG_BANG    = "BIG_BANG"
    PHASED      = "PHASED"
    INCREMENTAL = "INCREMENTAL"
    CDC_BASED   = "CDC_BASED"
    DUAL_WRITE  = "DUAL_WRITE"
    DRY_RUN     = "DRY_RUN"
    SIMULATION  = "SIMULATION"


# ---------------------------------------------------------------------------
# System Types — 17 DB/Storage + Cloud Storage
# ---------------------------------------------------------------------------

class SystemType(str, Enum):
    # Relational Databases (RDBMS)
    ORACLE      = "ORACLE"
    POSTGRESQL  = "POSTGRESQL"
    MYSQL       = "MYSQL"
    MARIADB     = "MARIADB"
    MSSQL       = "MSSQL"
    IBM_DB2     = "IBM_DB2"
    SQLITE      = "SQLITE"

    # Data Warehouses & Big Data
    SNOWFLAKE   = "SNOWFLAKE"
    BIGQUERY    = "BIGQUERY"
    REDSHIFT    = "REDSHIFT"
    HDFS        = "HDFS"

    # NoSQL, Graph, Key-Value & Search
    MONGODB     = "MONGODB"
    CASSANDRA   = "CASSANDRA"
    NEO4J       = "NEO4J"
    REDIS       = "REDIS"
    ELASTICSEARCH = "ELASTICSEARCH"

    # Cloud Object Storage
    S3          = "S3"
    GCS         = "GCS"
    AZURE_BLOB  = "AZURE_BLOB"

    GENERIC     = "GENERIC"


# ---------------------------------------------------------------------------
# Cloud Platforms — 9 platforms
# ---------------------------------------------------------------------------

class CloudPlatform(str, Enum):
    AWS           = "AWS"
    AZURE         = "AZURE"
    GCP           = "GCP"
    OCI           = "OCI"           # Oracle Cloud Infrastructure
    IBM_CLOUD     = "IBM_CLOUD"
    DIGITALOCEAN  = "DIGITALOCEAN"
    PRIVATE_CLOUD = "PRIVATE_CLOUD" # OpenStack, VMware
    HYBRID_CLOUD  = "HYBRID_CLOUD"
    ON_PREMISE    = "ON_PREMISE"


# ---------------------------------------------------------------------------
# Adapter Capability Flags
# ---------------------------------------------------------------------------

class AdapterCapability(str, Enum):
    SCHEMA_DISCOVERY  = "SCHEMA_DISCOVERY"
    BULK_READ         = "BULK_READ"
    STREAMING_READ    = "STREAMING_READ"
    BULK_WRITE        = "BULK_WRITE"
    STREAMING_WRITE   = "STREAMING_WRITE"
    CDC_SUPPORT       = "CDC_SUPPORT"
    TRANSACTION_SUPPORT = "TRANSACTION_SUPPORT"
    OBJECT_STORAGE    = "OBJECT_STORAGE"


# ---------------------------------------------------------------------------
# Queue Names
# ---------------------------------------------------------------------------

class QueueName(str, Enum):
    DISCOVERY    = "DISCOVERY_QUEUE"
    VALIDATION   = "VALIDATION_QUEUE"
    MIGRATION    = "MIGRATION_QUEUE"
    RECOVERY     = "RECOVERY_QUEUE"
    NOTIFICATION = "NOTIFICATION_QUEUE"
    REPORT       = "REPORT_QUEUE"


# ---------------------------------------------------------------------------
# Loop Governor
# ---------------------------------------------------------------------------

class LoopDecision(str, Enum):
    RETRY   = "RETRY"
    STOP    = "STOP"
    ESCALATE = "ESCALATE"
    RESTORE = "RESTORE_CHECKPOINT"
    FREEZE  = "FREEZE_SYSTEM"


class IncidentSeverity(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Input Gateway
# ---------------------------------------------------------------------------

class FileFormat(str, Enum):
    SQL  = "SQL"
    JSON = "JSON"
    CSV  = "CSV"


class GatewayStatus(str, Enum):
    PENDING    = "PENDING"
    VALIDATING = "VALIDATING"
    DETECTED   = "DETECTED"
    FORWARDED  = "FORWARDED"
    REJECTED   = "REJECTED"
    FAILED     = "FAILED"


# ---------------------------------------------------------------------------
# Risk Levels (from advisory layer)
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"
