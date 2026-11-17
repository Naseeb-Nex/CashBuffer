from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_INTERVALS = (15, 30, 60, 360, 1440)
AllowedInterval = Literal[15, 30, 60, 360, 1440]

class IngressConfigResponse(BaseModel):
    id: str
    household_id: str
    user_id: str
    provider: str = "gmail"
    is_enabled: bool
    interval_minutes: int
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    status: str = "idle"
    last_error: str | None = None
    created_at: datetime | None = None

class UpdateIngressConfigRequest(BaseModel):
    interval_minutes: int | None = Field(None, description="Polling interval in minutes (15, 30, 60, 360, 1440)")
    is_enabled: bool | None = Field(None, description="Enable or disable automated sync")
    provider: str = Field("gmail", description="Ingress provider")

    @field_validator("interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v not in ALLOWED_INTERVALS:
            raise ValueError(f"interval_minutes must be one of {ALLOWED_INTERVALS}, got {v}")
        return v

# Alias for compatibility with Clean Architecture spec
UpdateConfig = UpdateIngressConfigRequest

class IngressTriggerResponse(BaseModel):
    message: str = "Sync triggered successfully"
    next_run_at: datetime
    status: str
    config: IngressConfigResponse

class IngressStatusResponse(BaseModel):
    household_id: str
    provider: str = "gmail"
    status: str
    is_enabled: bool
    interval_minutes: int
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_error: str | None = None
    total_processed: int = 0
    last_history_id: str | None = None
    last_email_internal_date: int | None = None
    checkpoint_updated_at: datetime | None = None
