# app/api/v1/search.py
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.embeddings import semantic_search
from app.services.llm import answer_with_rag
from app.services.graph import get_kg_context_for_products

router = APIRouter(tags=["search"])


# -----------------------------
#  Category synonyms (Hunnit)
# -----------------------------
CATEGORY_SYNONYMS: Dict[str, List[str]] = {
    "hoodie": [
        "hoodie",
        "hoodies",
        "gym hoodie",
        "gym hoodies",
        "workout hoodie",
        "workout hoodies",
        "active hoodie",
        "fleece hoodie",
        "oversized hoodie",
        "oversized hoodies",
        "zip hoodie",
        "zip-up hoodie",
        "full zip hoodie",
        "cropped hoodie",
        "hooded jacket",
        "hooded sweatshirt",
        "sweat jacket",
    ],
    "tshirt": [
        "tshirt",
        "t-shirt",
        "tee",
        "tees",
        "crew neck",
        "crew-neck tee",
        "round neck",
        "top",
        "tank top",
        "tank",
        "crop top",
        "cropped tee",
        "training top",
        "gym top",
        "workout top",
    ],
    "shorts": [
        "shorts",
        "gym shorts",
        "workout shorts",
        "sports shorts",
        "active shorts",
        "running shorts",
        "biker shorts",
        "high-waisted shorts",
        "co-ord shorts",
        "shorts co-ord",
        "bottoms",
        "active bottom",
        "sport bottom",
    ],
}


def detect_intent_category(query: str) -> str | None:
    """Guess which category user is talking about (hoodie / tshirt / shorts)."""
    q = query.lower()
    for cat, syns in CATEGORY_SYNONYMS.items():
        if any(syn in q for syn in syns):
            return cat
    return None


def enrich_query(query: str, category: str | None) -> str:
    """Append synonyms to the query so embeddings get stronger signal."""
    if category and category in CATEGORY_SYNONYMS:
        extra = " ".join(CATEGORY_SYNONYMS[category])
        return f"{query} {extra}"
    return query


class SearchRequest(BaseModel):
    query: str


def _compute_mention_bonus(prod: Dict[str, Any], answer_text: str) -> float:
    """
    Give extra score if product title/category words appear in LLM answer.
    This is what forces 'Essential Cropped Jacket' type items to the top
    when bot explicitly recommends them in text.
    """
    if not answer_text:
        return 0.0

    ans = answer_text.lower()
    title = (prod.get("title") or "").lower()
    category = (prod.get("category") or "").lower()

    bonus = 0.0

    # Full title match (strong)
    if title and title in ans:
        bonus += 0.7
    else:
        # Partial title word matches (medium)
        for tok in title.replace("-", " ").split():
            tok = tok.strip()
            if len(tok) >= 4 and tok in ans:
                bonus += 0.15

    # Category name mentioned (small)
    if category and category in ans:
        bonus += 0.1

    return bonus


def _run_search(query: str, db: Session) -> Dict[str, Any]:
    # 1) Detect category + enrich query for embeddings
    intent_category = detect_intent_category(query)
    enriched_query = enrich_query(query, intent_category)

    # 2) Vector search (take a bit more, we'll re-rank later)
    points = semantic_search(enriched_query, limit=10)
    if not points:
        return {"answer": "I couldn't find any relevant products.", "results": []}

    rag_chunks: List[str] = []
    product_map: Dict[int, Dict[str, Any]] = {}
    product_scores: List[tuple[int, float]] = []

    for p in points:
        payload = p.payload or {}
        pid = payload.get("product_id")
        if pid is None:
            continue

        title = payload.get("title") or ""
        category = payload.get("category") or ""
        price = payload.get("price")
        description = payload.get("description") or ""
        image_url = payload.get("image_url") or ""
        product_url = payload.get("product_url") or ""
        chunk_text = payload.get("chunk_text") or ""

        # RAG context
        rag_chunks.append(
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"Price: {price}\n"
            f"Description: {description}\n"
            f"Snippet: {chunk_text}"
        )

        # Best score per product_id
        if pid not in product_map or p.score > product_map[pid]["score"]:
            product_map[pid] = {
                "id": pid,
                "title": title,
                "category": category,
                "price": price,
                "description": description,
                "image_url": image_url,
                "product_url": product_url,
                "score": float(p.score or 0.0),
            }

        product_scores.append((pid, float(p.score or 0.0)))

    if not product_map:
        return {"answer": "I couldn't find any relevant products.", "results": []}

    # Order by semantic score first (so context is still high quality)
    ordered_ids: List[int] = []
    seen: set[int] = set()
    for pid, _ in sorted(product_scores, key=lambda x: -x[1]):
        if pid not in seen:
            ordered_ids.append(pid)
            seen.add(pid)

    base_results = [product_map[pid] for pid in ordered_ids]

    # 3) Add KG conceptual context
    kg_chunks = get_kg_context_for_products(ordered_ids)
    rag_chunks.extend(kg_chunks)

    # 4) Ask LLM for final answer
    answer = answer_with_rag(query, rag_chunks)
    answer_text = answer or ""
    answer_lower = answer_text.lower()

    # 5) Re-rank results using "mentioned in answer" bonus
    #    → ensures the product that bot talks about first
    #      appears as the first card.
    def final_score(prod: Dict[str, Any]) -> float:
        base = float(prod.get("score") or 0.0)
        bonus = _compute_mention_bonus(prod, answer_lower)
        return base + bonus

    reranked_results = sorted(base_results, key=final_score, reverse=True)

    # Optional: cap to top N cards (e.g. 6) so UI clean rahe
    TOP_N = 6
    final_results = reranked_results[:TOP_N]

    return {"answer": answer_text, "results": final_results}


@router.get("/search", summary="Semantic product search with RAG + KG + LLM-aware ranking")
def search_products(
    query: str = Query(..., description="User question or search query"),
    db: Session = Depends(get_db),
):
    return _run_search(query, db)


@router.post("/search", summary="Semantic product search with RAG + KG + LLM-aware ranking")
def search_products_post(
    body: SearchRequest,
    db: Session = Depends(get_db),
):
    """
    POST variant so the frontend can send JSON: { "query": "hoodies" }.
    """
    return _run_search(body.query, db)
