# app/services/embeddings.py
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.product import Product

_embedder: SentenceTransformer | None = None
_qdrant: QdrantClient | None = None
_VECTOR_DIM: int | None = None

# 👉 Must match "Vector name" in Qdrant collection UI
QDRANT_VECTOR_NAME = "product_vector"


def get_embedder() -> SentenceTransformer:
    """
    Global singleton for sentence-transformers embedder.
    """
    global _embedder, _VECTOR_DIM
    if _embedder is None:
        _embedder = SentenceTransformer(settings.BGE_MODEL_NAME)
        _VECTOR_DIM = _embedder.get_sentence_embedding_dimension()
    return _embedder


def get_qdrant() -> QdrantClient:
    """
    Global singleton for Qdrant client.
    """
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
    return _qdrant


def ensure_collection() -> None:
    """
    Make sure the Qdrant collection exists with correct vector size
    and named vector config.
    """
    client = get_qdrant()
    embedder = get_embedder()
    vector_dim = _VECTOR_DIM or embedder.get_sentence_embedding_dimension()

    collections = client.get_collections().collections
    names = {c.name for c in collections}
    if settings.QDRANT_COLLECTION in names:
        return

    # Create collection with a NAMED dense vector
    client.create_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config={
            QDRANT_VECTOR_NAME: qmodels.VectorParams(
                size=vector_dim,
                distance=qmodels.Distance.COSINE,
            )
        },
    )


def _product_to_text(product: Product) -> str:
    """
    Convert a product row into a single text string for embeddings.
    Uses title, category, description, and features.
    """
    if isinstance(product.features, (dict, list)):
        features_text = str(product.features)
    else:
        features_text = product.features or ""

    parts: List[str] = [
        product.title or "",
        product.category or "",
        product.description or "",
        features_text,
    ]
    # Filter empty strings and join
    return "\n".join([p for p in parts if p])


def index_all_products(db: Session, skip_if_indexed: bool = False) -> int:
    """
    Fetch all products from Neon Postgres and upsert into Qdrant.
    Returns number of indexed products.

    If skip_if_indexed=True and collection already has points,
    we don't re-index.
    """
    ensure_collection()
    client = get_qdrant()
    embedder = get_embedder()

    if skip_if_indexed:
        info = client.get_collection(settings.QDRANT_COLLECTION)
        if info.points_count and info.points_count > 0:
            print(
                f"ℹ️ Qdrant collection '{settings.QDRANT_COLLECTION}' "
                f"already has {info.points_count} points — skipping re-index on startup."
            )
            return 0

    products: List[Product] = db.query(Product).all()
    if not products:
        return 0

    ids: List[int] = []
    vectors: List[List[float]] = []
    payloads: List[dict] = []

    texts = [_product_to_text(p) for p in products]
    embeddings = embedder.encode(texts, normalize_embeddings=True)

    for product, vector in zip(products, embeddings):
        ids.append(product.id)
        vectors.append(vector.tolist())

        payloads.append(
            {
                "product_id": product.id,
                "title": product.title,
                "category": product.category,
                "description": product.description,
                "price": float(product.price) if product.price is not None else None,
                "image_url": product.image_url,
                "product_url": product.product_url,
            }
        )

    # 👉 Upsert with NAMED vector
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=qmodels.Batch(
            ids=ids,
            vectors={QDRANT_VECTOR_NAME: vectors},
            payloads=payloads,
        ),
    )

    return len(products)


def semantic_search(
    query: str,
    limit: int = 5,
    allowed_product_ids: Optional[List[int]] = None,
) -> List[qmodels.ScoredPoint]:
    """
    Run semantic search in Qdrant for a free-text query.

    If allowed_product_ids is provided and non-empty, we restrict
    search to those product_ids using a Qdrant payload filter.
    """
    ensure_collection()
    client = get_qdrant()
    embedder = get_embedder()

    q_vec = embedder.encode([query], normalize_embeddings=True)[0].tolist()

    query_filter = None
    if allowed_product_ids:
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="product_id",
                    match=qmodels.MatchAny(any=allowed_product_ids),
                )
            ]
        )

    # 👉 Use NamedVector for named collection vector
    results = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=qmodels.NamedVector(
            name=QDRANT_VECTOR_NAME,
            vector=q_vec,
        ),
        limit=limit,
        query_filter=query_filter,
    )
    return results
