"""
Configuration Profile Specifications.
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


class ProfileSpec(BaseModel):
    profile_name: str
    rest_port: int = 8000
    grpc_port: int = 50051
    max_payload_bytes: int = 10485760  # 10MB
    rate_limit_requests: int = 1000
    rate_limit_window_s: int = 60
    enable_cors: bool = False
    enable_mtls: bool = False
    secret_vault_url: Optional[str] = None
    custom_options: Dict[str, Any] = Field(default_factory=dict)
