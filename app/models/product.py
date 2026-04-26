from typing import Optional
from pydantic import BaseModel, Field, field_validator


def _round_price(value: float | None) -> float | None:
    """Normalize price to 2 decimal places. Shared by both Pydantic models."""
    return round(value, 2) if value is not None else None


class ProductCreate(BaseModel):
    """
    Validates the request body for POST /products.

    Why validate here instead of in the route or the database?
    Validating at the edge — the moment data enters the system — means bad data
    never reaches MongoDB. The caller gets a specific error message immediately
    rather than a cryptic database error or silent corruption later.
    """
    # Field(...) means required — the ... is Python's way of saying "no default, must be provided"
    # min_length/max_length prevent empty strings and unreasonably long values
    product_name: str = Field(..., min_length=1, max_length=200)
    product_category: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0.0)       # ge = greater than or equal to — prevents negative prices
    available_quantity: int = Field(..., ge=0)

    @field_validator("price")
    @classmethod
    def round_price(cls, value: float) -> float:
        # Floating-point math can produce values like 19.999999999 — rounding here
        # ensures the database always holds clean values like 20.0
        return _round_price(value)


class ProductUpdate(BaseModel):
    """
    Validates the request body for PUT /products/{id}.

    Why a separate class from ProductCreate?
    Updates should only change the fields you explicitly send — if you just want
    to update the price, you shouldn't need to re-send the name and category.
    Every field defaults to None so Pydantic accepts a partial body. The service
    uses model_dump(exclude_unset=True) to retrieve only the fields the client
    actually provided, so omitted fields and explicit nulls are correctly distinguished.
    """
    # None default allows partial payloads — exclude_unset=True in the service skips unset fields
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    product_category: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, ge=0.0)
    available_quantity: Optional[int] = Field(None, ge=0)

    @field_validator("price", mode="before")
    @classmethod
    def round_price(cls, value: Optional[float]) -> Optional[float]:
        return _round_price(value)
