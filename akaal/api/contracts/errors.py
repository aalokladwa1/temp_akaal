"""
Enterprise Error Hierarchy & Data Contracts for AKAAL Platform 7.
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


class AkaalError(Exception):
    """Base exception for all Platform 7 Enterprise errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "status_code": self.status_code,
        }


class AuthenticationError(AkaalError):
    code = "AUTHENTICATION_FAILED"
    status_code = 401


class AuthorizationError(AkaalError):
    code = "AUTHORIZATION_DENIED"
    status_code = 403


class ResourceNotFoundError(AkaalError):
    code = "RESOURCE_NOT_FOUND"
    status_code = 404


class ValidationError(AkaalError):
    code = "VALIDATION_FAILED"
    status_code = 422


class RateLimitExceededError(AkaalError):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429


class IdempotencyError(AkaalError):
    code = "IDEMPOTENCY_CONFLICT"
    status_code = 409


class CircuitBreakerOpenError(AkaalError):
    code = "CIRCUIT_BREAKER_OPEN"
    status_code = 503


class FacadeError(AkaalError):
    code = "FACADE_INVOCATION_FAILED"
    status_code = 502


class PluginError(AkaalError):
    code = "PLUGIN_EXECUTION_ERROR"
    status_code = 500


class ConfigurationError(AkaalError):
    code = "CONFIGURATION_ERROR"
    status_code = 500


class ErrorResponse(BaseModel):
    """Canonical Error Response DTO for Platform 7 APIs."""

    error_code: str = Field(..., description="Unique enterprise error code string")
    message: str = Field(..., description="Human-readable description of error")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured error details")
