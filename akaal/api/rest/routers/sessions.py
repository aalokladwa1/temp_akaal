"""
Session REST API Router (/api/v1/sessions).
"""

import datetime
import uuid
from fastapi import APIRouter
from akaal.api.contracts.dto import SessionDTO

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionDTO)
async def create_session(user_id: str, tenant_id: str):
    """Create a migration session."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(hours=8)
    return SessionDTO(
        session_id=f"sess-{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        tenant_id=tenant_id,
        created_at=now.isoformat(),
        expires_at=expires.isoformat(),
        is_active=True,
    )
