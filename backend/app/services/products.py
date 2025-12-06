from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app import models
from app.schemas.product import ProductCreate, ProductUpdate

def get_product(db: Session, product_id: int) -> models.Product:
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )
    return product

def list_products(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
) -> List[models.Product]:
    query = db.query(models.Product)
    if category:
        query = query.filter(models.Product.category == category)
    return query.offset(skip).limit(limit).all()

def create_product(db: Session, product_in: ProductCreate) -> models.Product:
    product = models.Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

def update_product(
    db: Session,
    product_id: int,
    product_in: ProductUpdate,
) -> models.Product:
    product = get_product(db, product_id)
    for field, value in product_in.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product
