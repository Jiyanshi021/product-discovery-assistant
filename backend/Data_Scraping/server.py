import os
from datetime import datetime
from typing import List, Optional
from rag_pipeline import (
    index_products,
    retrieve_products,
    generate_recommendation_answer,
)

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    JSON,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Import scraper helpers from scrap.py
from scrap import (
    get_product_links_from_collection,
    parse_hunnit_product,
    HUNNIT_COLLECTION_URL,
)

# ---------- CONFIG ----------

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment variables")

# SQLAlchemy engine & session
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()

app = FastAPI(title="Hunnit Product API (Neon + FastAPI)")


# ---------- DATABASE MODEL ----------

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    price = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    # Stores dict: {"product_features": [...], "fabric_features": [...], "function": [...]}
    features = Column(JSON, nullable=True)
    image_url = Column(String(1024), nullable=True)
    category = Column(String(255), nullable=True)
    product_url = Column(String(1024), nullable=False, unique=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# Create tables if not exist
Base.metadata.create_all(bind=engine)


# ---------- Pydantic SCHEMAS ----------

class FeaturesSchema(BaseModel):
    product_features: List[str] = []
    fabric_features: List[str] = []
    function: List[str] = []


class ProductBaseSchema(BaseModel):
    title: str
    price: Optional[float] = None
    description: Optional[str] = None
    features: Optional[FeaturesSchema] = None
    image_url: Optional[HttpUrl] = None
    category: Optional[str] = None
    product_url: HttpUrl


class ProductReadSchema(ProductBaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # allow SQLAlchemy -> Pydantic


class ScrapeResponseSchema(BaseModel):
    status: str
    collection_url: str
    products_scraped: int
    created: int
    updated: int


class IndexResponseSchema(BaseModel):
    status: str
    products_indexed: int
    chunks_indexed: int


class ChatRequestSchema(BaseModel):
    query: str
    top_k: int = 5


class ChatProductSchema(ProductReadSchema):
    score: float


class ChatResponseSchema(BaseModel):
    query: str
    answer: str
    products: List[ChatProductSchema]


# ---------- DB DEPENDENCY ----------

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- ENDPOINTS ----------

@app.post("/scrape/hunnit", response_model=ScrapeResponseSchema)
def scrape_hunnit(max_products: int = 40, db: Session = Depends(get_db)):
    """
    Scrape Hunnit Jackets & Hoodies collection and upsert into Neon PostgreSQL.
    """
    product_links = get_product_links_from_collection(max_products=max_products)

    created = 0
    updated = 0

    for url in product_links:
        try:
            product_data = parse_hunnit_product(url)
        except HTTPException:
            # bubble up HTTPException from scraper
            raise
        except Exception as e:
            print(f"Error parsing {url}: {e}")
            continue

        if not product_data.get("title"):
            # skip weird pages without title
            continue

        existing: Optional[Product] = (
            db.query(Product)
            .filter(Product.product_url == product_data["product_url"])
            .one_or_none()
        )

        if existing:
            # Update existing row
            existing.title = product_data.get("title")
            existing.price = product_data.get("price")
            existing.description = product_data.get("description")
            existing.features = product_data.get("features")
            existing.image_url = product_data.get("image_url")
            existing.category = product_data.get("category")
            updated += 1
        else:
            # Insert new row
            new_product = Product(
                title=product_data.get("title"),
                price=product_data.get("price"),
                description=product_data.get("description"),
                features=product_data.get("features"),
                image_url=product_data.get("image_url"),
                category=product_data.get("category"),
                product_url=product_data.get("product_url"),
            )
            db.add(new_product)
            created += 1

    db.commit()

    total_scraped = created + updated

    if total_scraped == 0:
        raise HTTPException(status_code=500, detail="No products parsed successfully")

    return ScrapeResponseSchema(
        status="ok",
        collection_url=HUNNIT_COLLECTION_URL,
        products_scraped=total_scraped,
        created=created,
        updated=updated,
    )

@app.post("/index-products", response_model=IndexResponseSchema)
def index_all_products(db: Session = Depends(get_db)):
    """
    Load all products from PostgreSQL and index them in Qdrant
    using bge-m3 embeddings.
    """
    products = db.query(Product).order_by(Product.id).all()
    if not products:
        raise HTTPException(status_code=400, detail="No products in DB to index")

    # convert to plain dicts that rag_pipeline expects
    product_dicts = []
    for p in products:
        product_dicts.append(
            {
                "id": p.id,
                "title": p.title,
                "price": p.price,
                "description": p.description,
                "features": p.features or {},
                "image_url": p.image_url,
                "category": p.category,
                "product_url": p.product_url,
            }
        )

    chunks_indexed = index_products(product_dicts)

    return IndexResponseSchema(
        status="ok",
        products_indexed=len(product_dicts),
        chunks_indexed=chunks_indexed,
    )


@app.post("/chat/recommend", response_model=ChatResponseSchema)
def chat_recommend(
    payload: ChatRequestSchema,
    db: Session = Depends(get_db),
):
    """
    RAG-style recommendation endpoint.

    1) Embed user query with bge-m3
    2) Retrieve top products from Qdrant
    3) Fetch full product rows from DB
    4) Ask LLM to choose + explain recommendations
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")

    retrieved = retrieve_products(payload.query, top_k=payload.top_k)
    if not retrieved:
        # still involve LLM to ask clarifying question
        answer = generate_recommendation_answer(payload.query, [])
        return ChatResponseSchema(query=payload.query, answer=answer, products=[])

    # fetch product rows from DB
    id_to_score = {r.product_id: r.score for r in retrieved}
    product_rows = (
        db.query(Product)
        .filter(Product.id.in_(list(id_to_score.keys())))
        .all()
    )

    # map to dicts for LLM context
    prod_dicts = []
    for p in product_rows:
        prod_dicts.append(
            {
                "id": p.id,
                "title": p.title,
                "price": p.price,
                "description": p.description,
                "features": p.features or {},
                "category": p.category,
                "product_url": p.product_url,
            }
        )

    # pair with similarity scores
    snippets = [(prod, id_to_score[prod["id"]]) for prod in prod_dicts]
    answer = generate_recommendation_answer(payload.query, snippets)

    # Build response products list (sorted by score)
    chat_products: List[ChatProductSchema] = []
    for prod in sorted(snippets, key=lambda x: x[1], reverse=True):
        pdict, score = prod
        row = next((r for r in product_rows if r.id == pdict["id"]), None)
        if not row:
            continue

        chat_products.append(
            ChatProductSchema(
                id=row.id,
                title=row.title,
                price=row.price,
                description=row.description,
                features=row.features or {},
                image_url=row.image_url,
                category=row.category,
                product_url=row.product_url,
                created_at=row.created_at,
                updated_at=row.updated_at,
                score=score,
            )
        )

    return ChatResponseSchema(
        query=payload.query,
        answer=answer,
        products=chat_products,
    )


@app.get("/products", response_model=List[ProductReadSchema])
def list_products(db: Session = Depends(get_db)):
    """
    JSON list of all products stored in Neon DB.
    """
    products = db.query(Product).order_by(Product.id).all()
    return products


@app.get("/products/{product_id}", response_model=ProductReadSchema)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    JSON detail of a single product by ID.
    """
    product = db.query(Product).filter(Product.id == product_id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/debug/products-table", response_class=HTMLResponse)
def products_table_view(db: Session = Depends(get_db)):
    """
    Simple HTML table view to visually inspect DB data in browser.
    """
    products = db.query(Product).order_by(Product.id).all()

    rows_html = ""
    for p in products:
        if p.description and len(p.description) > 120:
            short_desc = p.description[:120] + "…"
        else:
            short_desc = p.description or ""

        rows_html += f"""
        <tr>
            <td>{p.id}</td>
            <td>{p.title}</td>
            <td>{p.price if p.price is not None else ""}</td>
            <td>{p.category or ""}</td>
            <td><a href="{p.product_url}" target="_blank">Link</a></td>
            <td>{short_desc}</td>
            <td>{p.created_at}</td>
            <td>{p.updated_at}</td>
        </tr>
        """

    html = f"""
    <html>
      <head>
        <title>Products Table View</title>
        <style>
          body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 20px; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 14px; vertical-align: top; }}
          th {{ background-color: #f4f4f4; text-align: left; }}
          tr:nth-child(even) {{ background-color: #fafafa; }}
          a {{ color: #2563eb; text-decoration: none; }}
          a:hover {{ text-decoration: underline; }}
          h1 {{ margin-bottom: 16px; }}
        </style>
      </head>
      <body>
        <h1>Products (Neon DB)</h1>
        <p>Total: {len(products)}</p>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Price</th>
              <th>Category</th>
              <th>Product URL</th>
              <th>Description (short)</th>
              <th>Created At</th>
              <th>Updated At</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </body>
    </html>
    """
    return HTMLResponse(content=html)
