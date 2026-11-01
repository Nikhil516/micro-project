from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str
    colour: str = "unknown"
    pattern: str = "solid"
    sleeve_type: str = "unknown"
    description: str = ""


class ProductCreate(ProductBase):
    product_id: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    colour: Optional[str] = None
    pattern: Optional[str] = None
    sleeve_type: Optional[str] = None
    description: Optional[str] = None


class ProductOut(ProductBase):
    product_id: str
    image_url: Optional[str] = None
    image_embedding_ready: bool = False
    has_history: bool = False
    created_at: Optional[datetime] = None
