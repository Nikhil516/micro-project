from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class SaleIn(BaseModel):
    product_id: str
    date: date
    quantity: float = Field(ge=0)
    revenue: Optional[float] = None


class SaleOut(SaleIn):
    id: str
    created_at: Optional[datetime] = None


class WeeklySale(BaseModel):
    product_id: str
    week_start: date
    units: float
