# app/api/v1/product.py
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductOut, ProductCreate, ProductUpdate
from app.services import products as product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "/",
    response_model=List[ProductOut],
    status_code=status.HTTP_200_OK,
)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    """
    List products with optional category filter.
    Ye endpoint hi frontend ke HomePage se hit ho raha hai.
    """
    return product_service.list_products(db, skip=skip, limit=limit, category=category)


@router.get(
    "/{product_id}",
    response_model=ProductOut,
    status_code=status.HTTP_200_OK,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Get single product by DB id.
    Chat page ya detail page ke kaam ka.
    """
    return product_service.get_product(db, product_id=product_id)


@router.post(
    "/",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
):
    """
    Manually product create karne ke liye (ya scraper yahi call kare).
    """
    return product_service.create_product(db, product_in=product_in)


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    status_code=status.HTTP_200_OK,
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
):
    """
    Product update endpoint.
    """
    return product_service.update_product(db, product_id=product_id, product_in=product_in)
