# # app/services/embeddings.py
# from typing import List, Tuple

# from qdrant_client import QdrantClient
# from qdrant_client.http import models as qmodels
# from sentence_transformers import SentenceTransformer
# from sqlalchemy.orm import Session

# from app.core.config import settings
# from app.models.product import Product

# _embedder: SentenceTransformer | None = None
# _qdrant: QdrantClient | None = None
# _VECTOR_DIM: int | None = None


# def get_embedder() -> SentenceTransformer:
#     """
#     Global singleton for bge-m3 embedder.
#     """
#     global _embedder, _VECTOR_DIM
#     if _embedder is None:
#         _embedder = SentenceTransformer(settings.BGE_MODEL_NAME)
#         _VECTOR_DIM = _embedder.get_sentence_embedding_dimension()
#     return _embedder


# def get_qdrant() -> QdrantClient:
#     """
#     Global singleton for Qdrant client.
#     """
#     global _qdrant
#     if _qdrant is None:
#         _qdrant = QdrantClient(
#             url=settings.QDRANT_URL,
#             api_key=settings.QDRANT_API_KEY,
#         )
#     return _qdrant


# def ensure_collection() -> None:
#     """
#     Make sure the Qdrant collection exists with correct vector size.
#     """
#     client = get_qdrant()
#     embedder = get_embedder()
#     vector_dim = _VECTOR_DIM or embedder.get_sentence_embedding_dimension()

#     collections = client.get_collections().collections
#     names = {c.name for c in collections}
#     if settings.QDRANT_COLLECTION not in names:
#         client.create_collection(
#             collection_name=settings.QDRANT_COLLECTION,
#             vectors_config=qmodels.VectorParams(
#                 size=vector_dim,
#                 distance=qmodels.Distance.COSINE,
#             ),
#         )


# def _collection_has_points() -> bool:
#     """
#     Return True if the collection already has at least one point.
#     Uses scroll (version-agnostic), so indexing can be skipped on reload.
#     """
#     client = get_qdrant()
#     try:
#         points, _ = client.scroll(
#             collection_name=settings.QDRANT_COLLECTION,
#             limit=1,
#             with_payload=False,
#             with_vectors=False,
#         )
#         return len(points) > 0
#     except Exception as e:
#         print("⚠️ Could not check Qdrant collection points:", e)
#         return False


# def _chunk_text(text: str, max_chars: int = 512, overlap: int = 64) -> List[str]:
#     """
#     Simple character-based chunking with overlap.
#     Good enough for product descriptions.
#     """
#     text = (text or "").strip()
#     if not text:
#         return []

#     chunks: List[str] = []
#     start = 0
#     length = len(text)

#     while start < length:
#         end = min(start + max_chars, length)
#         chunk = text[start:end].strip()
#         if chunk:
#             chunks.append(chunk)
#         if end >= length:
#             break
#         start = end - overlap

#     return chunks


# def _product_to_chunks(product: Product) -> List[str]:
#     """
#     Convert a product row into multiple text chunks for embeddings.
#     We include title/category once and chunk description/features.
#     """
#     if isinstance(product.features, dict):
#         features_text = ", ".join(f"{k}: {v}" for k, v in product.features.items())
#     elif isinstance(product.features, list):
#         features_text = ", ".join(str(f) for f in product.features)
#     else:
#         features_text = product.features or ""

#     header_parts: List[str] = [
#         product.title or "",
#         product.category or "",
#     ]
#     header = " | ".join([p for p in header_parts if p])

#     body = " ".join(
#         [
#             product.description or "",
#             features_text,
#         ]
#     ).strip()

#     body_chunks = _chunk_text(body, max_chars=512, overlap=64)
#     if not body_chunks:
#         # if description is tiny, just one chunk from header
#         return [header] if header else []

#     chunks: List[str] = []
#     for chunk in body_chunks:
#         if header:
#             chunks.append(f"{header}\n{chunk}")
#         else:
#             chunks.append(chunk)

#     return chunks


# def index_all_products(db: Session, skip_if_indexed: bool = True) -> int:
#     """
#     Fetch all products from Neon Postgres and upsert chunks into Qdrant.
#     Returns number of *chunks* indexed.

#     If skip_if_indexed=True and the collection already has points,
#     indexing is skipped (so server reload doesn't re-store everything).
#     """
#     ensure_collection()
#     client = get_qdrant()
#     embedder = get_embedder()

#     if skip_if_indexed and _collection_has_points():
#         print(
#             f"ℹ️ Qdrant collection '{settings.QDRANT_COLLECTION}' already has points "
#             f"— skipping re-index on startup."
#         )
#         return 0

#     products: List[Product] = db.query(Product).all()
#     if not products:
#         return 0

#     # Build chunk list
#     all_chunk_texts: List[str] = []
#     chunk_meta: List[Tuple[Product, int, str]] = []  # (product, chunk_index, text)

#     for product in products:
#         chunks = _product_to_chunks(product)
#         for idx, chunk_text in enumerate(chunks):
#             chunk_meta.append((product, idx, chunk_text))
#             all_chunk_texts.append(chunk_text)

#     if not all_chunk_texts:
#         return 0

#     # Embed all chunks in one go
#     embeddings = embedder.encode(all_chunk_texts, normalize_embeddings=True)

#     ids: List[str] = []
#     vectors: List[List[float]] = []
#     payloads: List[dict] = []

#     for (product, idx, chunk_text), vector in zip(chunk_meta, embeddings):
#         ids.append(f"{product.id}_{idx}")  # unique per product-chunk
#         vectors.append(vector.tolist())

#         payloads.append(
#             {
#                 "product_id": product.id,
#                 "chunk_index": idx,
#                 "chunk_text": chunk_text,
#                 "title": product.title,
#                 "category": product.category,
#                 "description": product.description,
#                 "price": float(product.price) if product.price is not None else None,
#                 "image_url": product.image_url,
#                 "product_url": product.product_url,
#             }
#         )

#     client.upsert(
#         collection_name=settings.QDRANT_COLLECTION,
#         points=qmodels.Batch(
#             ids=ids,
#             vectors=vectors,
#             payloads=payloads,
#         ),
#     )

#     return len(ids)


# def semantic_search(query: str, limit: int = 5) -> List[qmodels.ScoredPoint]:
#     """
#     Run semantic search in Qdrant for a free-text query.
#     Returns matching chunks (each chunk has product_id + chunk_text in payload).
#     """
#     ensure_collection()
#     client = get_qdrant()
#     embedder = get_embedder()

#     q_vec = embedder.encode([query], normalize_embeddings=True)[0].tolist()

#     results = client.search(
#         collection_name=settings.QDRANT_COLLECTION,
#         query_vector=q_vec,
#         limit=limit,
#     )
#     return results





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


def get_embedder() -> SentenceTransformer:
    """
    Global singleton for bge-m3 embedder.
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
    Make sure the Qdrant collection exists with correct vector size.
    """
    client = get_qdrant()
    embedder = get_embedder()
    vector_dim = _VECTOR_DIM or embedder.get_sentence_embedding_dimension()

    collections = client.get_collections().collections
    names = {c.name for c in collections}
    if settings.QDRANT_COLLECTION in names:
        return

    client.create_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=qmodels.VectorParams(
            size=vector_dim,
            distance=qmodels.Distance.COSINE,
        ),
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
                f"already has points — skipping re-index on startup."
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

    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=qmodels.Batch(
            ids=ids,
            vectors=vectors,
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

    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=q_vec,
        limit=limit,
        query_filter=query_filter,
    )
    return results
