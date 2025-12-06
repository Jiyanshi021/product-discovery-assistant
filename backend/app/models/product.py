# app/models/product.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    JSON,
    DateTime,
    func,
)

from app.db.base import Base  # adjust if your Base is defined elsewhere


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # Neon DB fields (as per your schema)
    title = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    features = Column(JSON, nullable=True)       # JSON / JSONB
    image_url = Column(String, nullable=True)
    category = Column(String, nullable=True)
    product_url = Column(String, nullable=True)

    # Optional timestamps (if present / useful)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
