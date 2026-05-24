from pydantic import BaseModel, Field
from datetime import datetime


class CampaignModel(BaseModel):
    """Future grouping model for running calls against many appointments."""
    name: str
    appointment_ids: list[str] = Field(default_factory=list)
    status: str = "draft"
    created_at: datetime
    updated_at: datetime
