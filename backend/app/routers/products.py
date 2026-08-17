from __future__ import annotations

from fastapi import APIRouter

from app.products import PRODUCTS
from app.schemas import Product

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[Product])
async def list_products() -> list[Product]:
    return PRODUCTS
