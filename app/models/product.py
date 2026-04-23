from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    """
    Validates the request body for POST /products.
    All four fields are required. Pydantic raises ValidationError if any are
    missing, the wrong type, or violate a constraint (e.g. negative price).
    """
    product_name: str = Field(..., min_length=1, max_length=200)
    product_category: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0.0)           # ge = greater than or equal to
    available_quantity: int = Field(..., ge=0)

    @field_validator("price")
    @classmethod
    def round_price(cls, value: float) -> float:
        # Store prices rounded to 2 decimal places to avoid floating-point noise.
        # e.g. 19.999999999 → 20.0
        return round(value, 2)


class ProductUpdate(BaseModel):
    """
    Validates the request body for PUT /products/{id}.
    Every field is optional so the client can update just one field at a time
    without sending the entire document (PATCH semantics via PUT).
    """
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    product_category: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, ge=0.0)
    available_quantity: Optional[int] = Field(None, ge=0)

    @field_validator("price", mode="before")
    @classmethod
    def round_price(cls, value: Optional[float]) -> Optional[float]:
        return round(value, 2) if value is not None else None
