# from typing import Optional, List, Any
# from pydantic import BaseModel, Field

# class ProductBase(BaseModel):
#     title: str = Field(..., min_length=1, max_length=255)
#     price: Optional[float] = Field(None, ge=0)
#     currency: Optional[str] = Field(None, max_length=10)
#     description: Optional[str] = None
#     category: Optional[str] = Field(None, max_length=100)
#     image_url: Optional[str] = None
#     url: Optional[str] = None
#     features: Optional[List[str]] = None

# class ProductCreate(ProductBase):
#     external_id: Optional[str] = None

# class ProductUpdate(BaseModel):
#     title: Optional[str] = Field(None, min_length=1, max_length=255)
#     price: Optional[float] = Field(None, ge=0)
#     currency: Optional[str] = Field(None, max_length=10)
#     description: Optional[str] = None
#     category: Optional[str] = Field(None, max_length=100)
#     image_url: Optional[str] = None
#     url: Optional[str] = None
#     features: Optional[List[str]] = None

# class ProductOut(ProductBase):
#     id: int
#     external_id: Optional[str]
#     features: Optional[List[str]]
#     raw_json: Optional[Any] = None

#     class Config:
#         from_attributes = True  # Pydantic v2 style




# app/schemas/product.py
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None
    url: Optional[str] = None

    # IMPORTANT:
    # Hunnit scraper se features ek dict aa raha hai:
    # {
    #   "product_features": [...],
    #   "fabric_features": [...],
    #   "function": [...]
    # }
    # isliye yaha List[str] nahi, Any rakh rahe hain
    features: Optional[Any] = None


class ProductCreate(ProductBase):
    # scraping ke time hum external_id set kar sakte hain,
    # DB me nahi ho to bhi chale
    external_id: Optional[str] = None


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None
    url: Optional[str] = None
    features: Optional[Any] = None
    external_id: Optional[str] = None


class ProductOut(ProductBase):
    id: int

    # Yaha default = None zaroori hai, nahi to Pydantic isko required maanega
    external_id: Optional[str] = None

    # Explicitly Any, taaki dict/list/string sab accept ho jaaye
    features: Optional[Any] = None

    # Raw page JSON (agar tum store karte ho)
    raw_json: Optional[Any] = None

    class Config:
        # Pydantic v2 style – ORM model se attributes read karega
        from_attributes = True
