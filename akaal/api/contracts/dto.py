"""
Canonical Data Transfer Objects (DTOs) for AKAAL Platform 7.
"""

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
        def model_dump(self):
            return self.__dict__
    def Field(default=None, default_factory=None, **kwargs):
        return default


class JobRequestDTO(BaseModel):
    job_type: str = Field(..., description="Type of job to execute")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job execution payload")
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1-10)")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")


class JobResponseDTO(BaseModel):
    job_id: str
    status: str
    job_type: str
    created_at: str
    message: str = "Job created successfully"


class JobStatusDTO(BaseModel):
    job_id: str
    status: str
    progress_percentage: float = 0.0
    created_at: str
    updated_at: str
    error_message: Optional[str] = None


class WorkflowSubmitDTO(BaseModel):
    workflow_id: str
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = None


class WorkflowTraceDTO(BaseModel):
    workflow_id: str
    status: str
    total_steps: int
    executed_steps: List[str] = Field(default_factory=list)
    step_results: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0


class ClusterStatusDTO(BaseModel):
    cluster_id: str
    active_workers: int
    idle_workers: int
    total_capacity: int
    cluster_health: str = "HEALTHY"
    nodes: List[Dict[str, Any]] = Field(default_factory=list)


class WorkerScaleResultDTO(BaseModel):
    pool_name: str
    previous_count: int
    target_count: int
    status: str = "SCALING"


class SchemaCheckDTO(BaseModel):
    target_schema_name: str
    proposed_ddl: str
    compatibility_mode: str = "BACKWARD"


class SchemaCompatibilityResultDTO(BaseModel):
    is_compatible: bool
    schema_name: str
    compatibility_mode: str
    violations: List[str] = Field(default_factory=list)


class SchemaProposalDTO(BaseModel):
    proposal_id: str
    schema_name: str
    changes: List[Dict[str, Any]] = Field(default_factory=list)


class SchemaEvolutionResultDTO(BaseModel):
    proposal_id: str
    status: str
    applied_at: Optional[str] = None
    new_version: str


class CapabilityDTO(BaseModel):
    platform_name: str
    version: str
    supported_features: List[str] = Field(default_factory=list)
    active_protocols: List[str] = Field(default_factory=list)


class WebhookSubscriptionDTO(BaseModel):
    subscription_id: str
    target_url: str
    secret: str
    subscribed_events: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: str


class DeliveryRecordDTO(BaseModel):
    delivery_id: str
    subscription_id: str
    event_type: str
    status_code: int
    attempt_count: int
    success: bool
    timestamp: str
    error_message: Optional[str] = None


class EventEnvelopeDTO(BaseModel):
    event_id: str
    event_type: str
    producer: str = "akaal.platform7"
    timestamp: str
    tenant_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class SessionDTO(BaseModel):
    session_id: str
    user_id: str
    tenant_id: str
    created_at: str
    expires_at: str
    is_active: bool = True


class ValidationReportDTO(BaseModel):
    report_id: str
    target: str
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ReportDTO(BaseModel):
    report_id: str
    title: str
    report_type: str
    generated_at: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
