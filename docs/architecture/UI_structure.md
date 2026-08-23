AKAAL
│
│
├══════════════════════════════════════════════════════════════
│  1. DASHBOARD
├══════════════════════════════════════════════════════════════
│
├── Enterprise Overview
├── Active Migrations
├── Migration Health
├── Risk / Blockers
├── Pending Approvals
├── Alerts / Incidents
├── Platform Health
├── Capacity Summary
├── Fleet / Cluster Summary
├── Security / Compliance Summary
└── Recent Activity
│
│
│
├══════════════════════════════════════════════════════════════
│  2. MIGRATION
├══════════════════════════════════════════════════════════════
│
├── 2.1 Migration Portfolio
│   ├── All Migrations
│   ├── Active
│   ├── Scheduled
│   ├── Attention Required
│   ├── Completed
│   ├── Failed / Interrupted
│   └── Archived
│
│
├── 2.2 Create Migration
│   │
│   └── 9-Step Creation Wizard
│       │
│       ├── STEP 1 — Migration Definition
│       │   ├── Identity / Description
│       │   ├── Business Context
│       │   ├── Owner
│       │   ├── Environment
│       │   ├── Priority
│       │   ├── Optional Project / Workspace
│       │   ├── Planning Mode
│       │   │   ├── Standard
│       │   │   └── Advanced
│       │   │
│       │   ├── Execution Mode
│       │   │   ├── M1 — Bulk Migration
│       │   │   ├── M2 — Bulk + CDC
│       │   │   ├── M3 — CDC / Continuous Replication
│       │   │   ├── M4 — Incremental Query / Polling
│       │   │   ├── M5 — State-Based Synchronization
│       │   │   ├── M6 — Schema Only
│       │   │   ├── M7 — Data Only
│       │   │   └── M8 — Validation / Reconciliation Only
│       │   │
│       │   ├── Migration Window
│       │   ├── Start from Template
│       │   └── Clone Migration
│       │
│       ├── STEP 2 — Source Instance
│       │   ├── Saved / New Connection
│       │   ├── Authentication
│       │   ├── Network Route
│       │   ├── Connector Properties
│       │   ├── Connectivity Test
│       │   └── Capability Discovery
│       │
│       ├── STEP 3 — Target Instance
│       │   ├── Saved / New Connection
│       │   ├── Authentication
│       │   ├── Network Route
│       │   ├── Connector Properties
│       │   ├── Connectivity Test
│       │   ├── Write Authority
│       │   ├── Capability Discovery
│       │   └── Source ↔ Target Compatibility
│       │
│       ├── STEP 4 — Discovery & Advanced Scope
│       │   │
│       │   ├── Discovery & Assessment
│       │   │   ├── Instance Topology
│       │   │   ├── Database / Catalog Discovery
│       │   │   ├── Schema / Namespace Discovery
│       │   │   ├── Object Discovery
│       │   │   ├── Metadata Inspection
│       │   │   ├── Dependency Analysis
│       │   │   ├── Compatibility Assessment
│       │   │   ├── Impact Assessment
│       │   │   └── Risk Assessment
│       │   │
│       │   └── Selection & Scope
│       │       ├── Database / Catalog Selection
│       │       ├── Schema / Namespace Selection
│       │       ├── Object Selection
│       │       ├── Include / Exclude Rules
│       │       ├── Patterns
│       │       ├── Column Projection
│       │       ├── Row Predicates
│       │       ├── Partition / Range Selection
│       │       ├── Sampling
│       │       ├── Dependency Warnings
│       │       ├── Selection Preview
│       │       └── Volume Estimation
│       │
│       ├── STEP 5 — Mapping & Data Controls Studio
│       │   │
│       │   ├── Mapping
│       │   │   ├── Schema Routing
│       │   │   ├── Object Mapping
│       │   │   ├── Column Mapping
│       │   │   ├── Rename / Reorder
│       │   │   ├── Merge / Split
│       │   │   ├── Defaults / Generated / Ignored
│       │   │   └── Mapping Preview
│       │   │
│       │   ├── Transformation & Cleansing
│       │   │   ├── Transformation Rules
│       │   │   ├── Expression Builder
│       │   │   ├── Normalization
│       │   │   ├── NULL / Default Handling
│       │   │   ├── Derived Fields
│       │   │   ├── Lookups
│       │   │   ├── Malformed Data Handling
│       │   │   ├── Reject / Quarantine
│       │   │   └── Before / After Preview
│       │   │
│       │   ├── Privacy
│       │   │   ├── Masking
│       │   │   ├── Redaction
│       │   │   ├── Hashing
│       │   │   ├── Pseudonymization
│       │   │   ├── Tokenization
│       │   │   ├── Format Preservation
│       │   │   └── Referential Consistency
│       │   │
│       │   ├── Data Quality & Conflict
│       │   │   ├── Deduplication
│       │   │   ├── Duplicate Detection
│       │   │   ├── Composite Uniqueness
│       │   │   ├── Survivor Rules
│       │   │   ├── Invalid Data Policies
│       │   │   ├── Collision Policies
│       │   │   ├── Quarantine
│       │   │   └── Conflict Policies
│       │   │
│       │   └── SQL & Hooks
│       │       ├── Pre / Post Migration SQL
│       │       ├── Object Hooks
│       │       ├── Session Hooks
│       │       ├── Parameters
│       │       ├── Ordering / Dependencies
│       │       ├── Transaction Semantics
│       │       ├── Timeout / Retry
│       │       ├── Safety Analysis
│       │       └── Approval Requirements
│       │
│       ├── STEP 6 — Enterprise Configuration Center
│       │   │
│       │   ├── Standard Mode
│       │   │   ├── Enterprise-Level Controls
│       │   │   ├── AKAAL Recommendations
│       │   │   └── Automatically Derived Low-Level Settings
│       │   │
│       │   ├── Advanced Mode
│       │   │   ├── Runtime / Orchestration
│       │   │   ├── Workers / Parallelism
│       │   │   ├── Partitioning
│       │   │   ├── Batching
│       │   │   ├── Connection Pools
│       │   │   ├── Queues / Buffers
│       │   │   ├── Backpressure
│       │   │   ├── Bandwidth
│       │   │   ├── Bulk Transport
│       │   │   ├── CDC
│       │   │   ├── Incremental / Polling
│       │   │   ├── State Synchronization
│       │   │   ├── Validation
│       │   │   ├── Checkpointing / Durable State
│       │   │   ├── Recovery
│       │   │   ├── Retry / Failure
│       │   │   ├── LOB Handling
│       │   │   ├── Performance
│       │   │   ├── Schema Evolution
│       │   │   ├── Cutover / Failback
│       │   │   ├── Scheduling
│       │   │   ├── Resource Limits
│       │   │   ├── Connector Controls
│       │   │   └── Scoped Dynamic Overrides
│       │   │       ├── Organization
│       │   │       ├── Environment
│       │   │       ├── Migration
│       │   │       ├── Execution Mode
│       │   │       ├── DAG Node
│       │   │       ├── Object
│       │   │       ├── Partition
│       │   │       └── Connector
│       │   │
│       │   └── Approval Barrier Configuration
│       │
│       ├── STEP 7 — Dynamic Migration Plan
│       │   ├── Logical Plan
│       │   ├── Dynamic Execution DAG
│       │   ├── Schema Actions
│       │   ├── Dependencies
│       │   ├── Execution Ordering
│       │   ├── Node Configuration / Overrides
│       │   ├── Approval Barriers
│       │   ├── Compatibility
│       │   ├── Risk
│       │   ├── Work / Resource Estimates
│       │   ├── Warnings / Blockers
│       │   ├── Plan Versions / Diff
│       │   ├── Dry Run
│       │   └── Plan Fingerprint
│       │
│       ├── STEP 8 — Governance & Readiness
│       │   ├── Preflight
│       │   ├── Environment / Capacity Readiness
│       │   ├── Permissions
│       │   ├── Security / Policy Checks
│       │   ├── Migration Policies
│       │   ├── Approval Barriers
│       │   ├── Approval Chain / Status
│       │   ├── Waivers / Exceptions
│       │   ├── Fingerprint Verification
│       │   └── Execution Authorization
│       │
│       └── STEP 9 — Review, Schedule & Initialize
│           ├── Final Review
│           ├── Compile Immutable ExecutionPlan
│           ├── ExecutionPlan Fingerprint
│           ├── Run Now
│           ├── Schedule
│           └── Initialize Durable Execution
│                    │
│                    ▼
│              MISSION CONTROL
│
│
├── 2.3 Projects & Workspaces
│   ├── Projects
│   ├── Workspaces
│   ├── Overview
│   ├── Assigned Migrations
│   ├── Owners / Members
│   ├── Environment
│   ├── Activity
│   ├── Assign Migration
│   └── Move Migration
│
│   Migration may be:
│   • independent
│   • created inside a project/workspace
│   • assigned later
│   • moved later with authorization
│
├── 2.4 Connections
│   ├── Connections
│   ├── Profiles
│   ├── Capabilities
│   ├── Connectivity Tests
│   ├── Network Routes / Tunnels
│   ├── Health
│   └── Connector Details
│
├── 2.5 Mission Control
│   │
│   ├── Overview
│   │   ├── Migration State
│   │   ├── Progress
│   │   ├── Current / Next Operation
│   │   ├── Execution DAG
│   │   ├── Throughput / ETA
│   │   ├── Warnings / Blockers
│   │   └── Approval Barriers
│   │
│   ├── Runtime
│   │   ├── Workers
│   │   ├── Partitions
│   │   ├── Queues
│   │   ├── Checkpoints
│   │   └── Runtime Events
│   │
│   ├── Controls
│   │   ├── Start
│   │   ├── Pause
│   │   ├── Resume
│   │   ├── Terminate
│   │   └── Recover
│   │
│   └── Capability-Driven Operations
│       │
│       ├── Bulk
│       │
│       ├── CDC
│       │   ├── Capture / Apply
│       │   ├── Lag / Backlog
│       │   ├── Transactions / Ordering
│       │   ├── Parallel Apply
│       │   ├── Schema Evolution
│       │   ├── Conflicts / Quarantine
│       │   ├── Bidirectional
│       │   ├── Catch-Up
│       │   └── Recovery
│       │
│       ├── Incremental / Polling
│       │
│       ├── State Synchronization
│       │
│       ├── Schema Execution
│       │
│       ├── Validation & Reconciliation
│       │   ├── Validation Levels
│       │   ├── Row Counts
│       │   ├── Checksums / Merkle
│       │   ├── Row / Column Comparison
│       │   ├── Mismatch Localization
│       │   ├── Reconciliation
│       │   ├── Governed Repair
│       │   └── Evidence
│       │
│       └── Cutover & Failback
│           ├── Readiness
│           ├── Source Quiescence
│           ├── Final Drain
│           ├── Final Validation
│           ├── Approval
│           ├── Atomic Commit
│           ├── Fencing
│           ├── Failback Evaluation
│           ├── Failback Execution
│           └── Recovery
│
│   NOTE:
│   Only capabilities relevant to the migration's mode,
│   connector capabilities and lifecycle are exposed.
│
├── 2.6 Validation Operations
│   ├── New Validation
│   ├── Active Validations
│   ├── Validation History
│   ├── Source / Target
│   ├── Scope
│   ├── Configuration
│   ├── Validation Levels
│   ├── Row Counts
│   ├── Checksums / Merkle
│   ├── Row / Column Comparison
│   ├── Mismatch Analysis
│   ├── Reconciliation
│   ├── Governed Repair
│   └── Evidence
│
├── 2.7 Migration History
│   ├── Lifecycle / Timeline
│   ├── Execution History
│   ├── Plan / Configuration History
│   ├── Approval History
│   ├── Validation History
│   ├── Cutover / Failback History
│   ├── Recovery History
│   └── Audit Trail
│
└── 2.8 Templates
    └── Available Migration Templates
        (creation/use surface; enterprise template
         ownership remains under Administration)
│
│
│
├══════════════════════════════════════════════════════════════
│  3. MONITORING
├══════════════════════════════════════════════════════════════
│
├── 3.1 Overview
│   ├── Platform Status
│   ├── Active Workloads
│   ├── Health
│   ├── Alerts
│   └── Capacity
│
├── 3.2 Migration Monitoring
│   ├── All Running Migrations
│   ├── Bulk
│   ├── CDC
│   ├── Incremental / Polling
│   ├── State Synchronization
│   ├── Schema / Data Operations
│   └── Validation Operations
│
│   NOTE:
│   Capability-driven. A Bulk-only migration does NOT
│   suddenly display meaningless CDC telemetry.
│
├── 3.3 Performance
│   ├── Throughput
│   ├── Latency
│   ├── Worker / Partition Performance
│   ├── Queue / Backpressure
│   ├── Resource Usage
│   ├── Bottlenecks
│   └── Historical Performance
│
├── 3.4 Health Center
│   ├── Platform
│   ├── Runtime / Engine
│   ├── Connectors
│   ├── Databases / Endpoints
│   ├── Queues / Buffers
│   ├── Storage
│   ├── IPC / Services
│   ├── Dependencies
│   └── Diagnostics
│
├── 3.5 Infrastructure & Fleet
│   ├── Fleet
│   │   ├── Nodes / Agents
│   │   ├── Workers
│   │   ├── Health
│   │   ├── Versions
│   │   ├── Assignments
│   │   └── Lifecycle
│   │
│   ├── Clusters
│   │   ├── Clusters / Nodes
│   │   ├── Workload Distribution
│   │   ├── Kubernetes Workloads
│   │   ├── Scaling / Autoscaling
│   │   ├── Failover
│   │   ├── Regions / Locality
│   │   └── Topology
│   │
│   └── Capacity
│       ├── CPU
│       ├── Memory
│       ├── Storage
│       ├── Network
│       ├── Queue Capacity
│       └── Forecasts
│
├── 3.6 Reliability Center
│   ├── Failures
│   ├── Recovery
│   ├── Checkpoints / Resume
│   ├── Restart History
│   ├── Resilience
│   ├── Anomalies
│   ├── RCA
│   └── Reliability History
│
├── 3.7 Alerts & Incidents
│   ├── Active Alerts
│   ├── Alert Rules
│   ├── Incidents
│   ├── Correlation
│   ├── Escalation
│   └── History
│
└── 3.8 Observability
    ├── Metrics
    ├── Logs
    ├── Distributed Traces
    ├── Services
    ├── Migration Correlation
    ├── Runtime Events
    └── OpenTelemetry
│
│
│
├══════════════════════════════════════════════════════════════
│  4. REPORTS
├══════════════════════════════════════════════════════════════
│
├── 4.1 Reports Catalog
│   ├── Migration
│   ├── Schema / Compatibility
│   ├── Validation / Reconciliation
│   ├── Data Quality
│   ├── Performance
│   ├── CDC
│   ├── Cutover / Failback
│   ├── Recovery / Reliability
│   ├── Security
│   ├── Compliance
│   ├── Governance / Approval
│   ├── Audit
│   ├── Infrastructure / Fleet
│   └── Executive
│
├── 4.2 Trust Certification
│   ├── Certification Status
│   ├── Migration Certification
│   ├── Validation Certification
│   └── Verification
│
└── 4.3 Evidence Portal
    ├── Evidence Explorer
    ├── Dossiers
    ├── Certificates
    ├── Evidence Packages
    ├── Integrity Verification
    ├── Export
    └── Archive
│
│
│
├══════════════════════════════════════════════════════════════
│  5. ADMINISTRATION
├══════════════════════════════════════════════════════════════
│
├── 5.1 Enterprise
│   ├── Enterprise Setup
│   ├── Organizations
│   ├── Workspaces
│   ├── Environments
│   ├── Ownership
│   └── Quotas / Limits
│
├── 5.2 People & Access
│   ├── Users
│   ├── Teams / Groups
│   ├── Roles
│   ├── Permissions
│   ├── RBAC
│   ├── ABAC
│   ├── JIT Access
│   └── Separation of Duties
│
├── 5.3 Governance Centre
│   ├── Policies
│   ├── Approval Chains
│   ├── Approver Groups
│   ├── Maker / Checker
│   ├── Privileged Operations
│   ├── Exceptions / Waivers
│   ├── Policy Simulation
│   └── Governance History
│
├── 5.4 Identity & Security
│   ├── SSO
│   │   ├── OIDC
│   │   └── SAML
│   ├── MFA
│   ├── LDAP / Active Directory
│   ├── SCIM
│   ├── Identity Federation
│   ├── Service / Workload Identity
│   ├── SPIFFE / SPIRE
│   ├── Certificates
│   ├── Secrets / Vault
│   ├── KMS / CMK / BYOK
│   └── Rotation
│
├── 5.5 Template & Configuration Library
│   ├── Migration Templates
│   ├── Mapping Templates
│   ├── Transformation Templates
│   ├── Privacy Policies
│   ├── Data Quality Policies
│   ├── Configuration Profiles
│   ├── Versions
│   ├── Promotion
│   ├── Import / Export
│   └── Deprecation
│
├── 5.6 Connector & Plugin Center
│   ├── Connector Registry
│   ├── Installed Connectors
│   ├── Capabilities
│   ├── Compatibility
│   ├── Certification
│   ├── Plugins
│   ├── Plugin Security / Lifecycle
│   └── SDK / Developer Configuration
│
├── 5.7 Cloud & Infrastructure Configuration
│   ├── Cloud Environments
│   │   ├── AWS
│   │   ├── Azure
│   │   ├── GCP
│   │   └── OCI
│   ├── Kubernetes Configuration
│   ├── Private Connectivity
│   ├── Hybrid Environments
│   ├── Regions
│   ├── Data Sovereignty
│   ├── Infrastructure as Code
│   └── GitOps
│
│   NOTE:
│   Configuration/registration lives here.
│   Live cluster/fleet operation lives in Monitoring.
│
├── 5.8 Compliance
│   ├── Control Frameworks
│   ├── GDPR
│   ├── PCI-DSS
│   ├── HIPAA
│   ├── SOC 2
│   ├── ISO-Oriented Controls
│   └── Compliance Evidence
│
├── 5.9 Audit
│   ├── Audit Policies
│   ├── Audit Trail
│   ├── Evidence Retention
│   └── Tamper Evidence
│
└── 5.10 Platform Administration
    ├── Nodes / Services
    ├── Deployment
    ├── Versions
    ├── Licensing
    ├── Updates
    └── Support / Diagnostics
│
│
│
├══════════════════════════════════════════════════════════════
│  6. SETTINGS
├══════════════════════════════════════════════════════════════
│
├── 6.1 General
├── 6.2 Appearance
│
├── 6.3 Runtime & Migration Defaults
│   ├── Runtime
│   ├── Workers / Parallelism
│   ├── Batching
│   ├── Queues
│   ├── Resource Limits
│   ├── Bulk
│   ├── CDC
│   ├── Incremental / Polling
│   ├── State Synchronization
│   ├── Validation
│   └── Recovery
│
├── 6.4 Connector Defaults
│
├── 6.5 Storage & Retention
│   ├── Checkpoints
│   ├── CDC Buffers
│   ├── Reports / Evidence
│   ├── Logs
│   └── Retention Policies
│
├── 6.6 Notifications
│   ├── Email
│   ├── Slack
│   ├── Microsoft Teams
│   ├── Webhooks
│   └── Escalation Defaults
│
├── 6.7 Integrations
│   ├── Observability Integrations
│   ├── Notification Integrations
│   ├── Catalog / Lineage Integrations
│   └── Installed Enterprise Integrations
│
├── 6.8 AI & Intelligence
│   ├── Assistant Configuration
│   ├── Planning Assistance
│   ├── Optimization
│   ├── RCA / Diagnostics
│   ├── Recommendation Policies
│   └── Predictive Operations
│
├── 6.9 Logging & Diagnostics
│   ├── Log Levels
│   ├── Diagnostics
│   ├── Tracing
│   └── Support Bundles
│
└── 6.10 Advanced
    ├── Capability Controls
    ├── Experimental Capabilities
    ├── Developer Options
    └── Internal Diagnostics


══════════════════════════════════════════════════════════════
 GLOBAL / CROSS-CUTTING EXPERIENCE
══════════════════════════════════════════════════════════════

├── AKAAL Assistant
│   ├── Context-Aware Assistance
│   ├── Migration Planning
│   ├── Schema / SQL Assistance
│   ├── Failure / RCA Assistance
│   ├── Performance Optimization
│   └── Natural-Language Platform Control
│
├── Global Search / Command Palette
│
├── Notification Center
│
├── Approval Inbox
│   ├── Awaiting My Approval
│   ├── Requested by Me
│   ├── Approval Barrier Context
│   ├── Plan Fingerprint / Diff
│   └── Approval History
│
├── Incident Indicator
├── Background Operations
├── User / Organization / Workspace / Environment Switcher
├── Contextual Help
└── Documentation

