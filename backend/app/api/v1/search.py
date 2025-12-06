# app/api/v1/search.py
from typing import List, Dict, Any, Set
import re

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.embeddings import semantic_search
from app.services.llm import answer_with_rag
from app.services.graph import (
    get_kg_context_for_products,
    get_candidate_product_ids_from_kg,
)

router = APIRouter(tags=["search"])


# ---------------------------------------------------------
#  Minimal category synonyms (query language → category)
#  Neo4j holds the true categories; this is only a hint.
# ---------------------------------------------------------
CATEGORY_SYNONYMS: Dict[str, List[str]] = {
    "hoodie": [
        "hoodie",
        "hoodies",
        "hooded sweatshirt",
        "hooded jacket",
        "zip hoodie",
        "oversized hoodie",
    ],
    "tshirt": [
        "tshirt",
        "t-shirt",
        "tee",
        "tees",
        "top",
        "crop top",
        "tank top",
        "training top",
        "gym top",
    ],
    "shorts": [
        "shorts",
        "running shorts",
        "biker shorts",
        "gym shorts",
        "workout shorts",
    ],
}


def detect_intent_category(query: str) -> str | None:
    """
    Guess which logical category the user is talking about
    (hoodie / tshirt / shorts) using a small synonyms map.
    """
    q = query.lower()
    for cat, syns in CATEGORY_SYNONYMS.items():
        if any(syn in q for syn in syns):
            return cat
    return None


def enrich_query(query: str, category: str | None) -> str:
    """
    Append a few synonyms to the query so embeddings
    get a stronger signal for the intended category.
    """
    if category and category in CATEGORY_SYNONYMS:
        extra = " ".join(CATEGORY_SYNONYMS[category])
        return f"{query} {extra}"
    return query


# ---------------------------------------------------------
#   Price + tag extraction from natural language query
# ---------------------------------------------------------

PRICE_PATTERN = re.compile(r"(under|below|upto|up to|<)\s*(\d+)", re.IGNORECASE)

STOPWORDS: Set[str] = {
    "show",
    "me",
    "some",
    "for",
    "under",
    "below",
    "upto",
    "up",
    "to",
    "please",
    "want",
    "need",
    "something",
    "nice",
    "good",
    "budget",
    "wear",
    "outfit",
    "and",
    "also",
}


def extract_max_price(query: str) -> float | None:
    """Extract max price from patterns like 'under 2000'."""
    m = PRICE_PATTERN.search(query)
    if not m:
        return None
    try:
        return float(m.group(2))
    except ValueError:
        return None


def extract_tags(query: str, category: str | None) -> List[str]:
    """
    Lightweight tag extraction for KG matching.
    Example: 'oversized hoodies for gym under 2000'
      → ['oversized', 'gym']
    """
    words = re.findall(r"[a-zA-Z]+", query.lower())
    tags = [w for w in words if len(w) >= 4 and w not in STOPWORDS]

    # Remove explicit category tokens so tags focus on style / use-case
    if category and category in CATEGORY_SYNONYMS:
        remove: Set[str] = set()
        for syn in CATEGORY_SYNONYMS[category]:
            for tok in syn.split():
                remove.add(tok.lower())
        tags = [t for t in tags if t not in remove]

    # Deduplicate but preserve order
    seen: Set[str] = set()
    unique_tags: List[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)
    return unique_tags


class SearchRequest(BaseModel):
    query: str


def _compute_mention_bonus(prod: Dict[str, Any], answer_text: str) -> float:
    """
    Give extra score if product title/category words appear in LLM answer.
    This forces the items the bot explicitly talks about to the top.
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
    # 1) Understand intent from the query
    intent_category = detect_intent_category(query)          # e.g. "hoodie"
    max_price = extract_max_price(query)                     # e.g. 2000
    tags = extract_tags(query, intent_category)              # e.g. ["oversized", "gym"]

    # Enrich query for embeddings (semantic layer)
    enriched_query = enrich_query(query, intent_category)

    # 2) Ask Neo4j KG for conceptual candidate product_ids
    #    This uses true categories + feature nodes.
    kg_candidate_ids: Set[int] = set()
    if intent_category or max_price or tags:
        try:
            kg_ids = get_candidate_product_ids_from_kg(
                category_hint=intent_category,  # can be None
                max_price=max_price,            # can be None
                tags=tags,                      # can be []
            )
            kg_candidate_ids = set(kg_ids or [])
        except Exception:
            # If KG is off / down, don't break search – just skip KG filter.
            kg_candidate_ids = set()

    # 3) Vector search in Qdrant (semantic layer)
    points = semantic_search(enriched_query, limit=20)
    if not points:
        msg = "I couldn't find any relevant products."
        if intent_category:
            msg = (
                f"I couldn't find any strong matches for {intent_category}s. "
                "Try rephrasing or relaxing your constraints."
            )
        return {"answer": msg, "results": []}

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

        score = float(p.score or 0.0)

        # Build RAG context out of all relevant chunks
        rag_chunks.append(
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"Price: {price}\n"
            f"Description: {description}\n"
            f"Snippet: {chunk_text}"
        )

        # Keep best score per product
        if pid not in product_map or score > product_map[pid]["score"]:
            product_map[pid] = {
                "id": pid,
                "title": title,
                "category": category,
                "price": price,
                "description": description,
                "image_url": image_url,
                "product_url": product_url,
                "score": score,
            }

        product_scores.append((pid, score))

    if not product_map:
        return {"answer": "I couldn't find any relevant products.", "results": []}

    # 4) Order products by raw semantic score
    ordered_ids: List[int] = []
    seen_ids: Set[int] = set()
    for pid, _ in sorted(product_scores, key=lambda x: -x[1]):
        if pid not in seen_ids:
            ordered_ids.append(pid)
            seen_ids.add(pid)

    # 4b) HYBRID: if KG returned candidates, restrict to them.
    #     This is where Neo4j actually influences what we surface.
    if kg_candidate_ids:
        filtered_ids = [pid for pid in ordered_ids if pid in kg_candidate_ids]
        # Only override if KG gave at least some overlap
        if filtered_ids:
            ordered_ids = filtered_ids

    base_results = [product_map[pid] for pid in ordered_ids]

    # 5) Add KG conceptual context for these products for RAG
    kg_chunks = get_kg_context_for_products(ordered_ids)
    rag_chunks.extend(kg_chunks)

    # 6) Ask LLM to synthesize an answer
    answer = answer_with_rag(query, rag_chunks)
    answer_text = answer or ""
    answer_lower = answer_text.lower()

    # 7) Re-rank products so the ones explicitly mentioned by LLM
    #    (by title / category) float to the top.
    def final_score(prod: Dict[str, Any]) -> float:
        base = float(prod.get("score") or 0.0)
        bonus = _compute_mention_bonus(prod, answer_lower)
        return base + bonus

    reranked_results = sorted(base_results, key=final_score, reverse=True)

    # 8) Keep only top-N for UI cleanliness
    TOP_N = 6
    final_results = reranked_results[:TOP_N]

    return {"answer": answer_text, "results": final_results}


@router.get(
    "/search",
    summary="Semantic product search with RAG + KG + LLM-aware ranking",
)
def search_products(
    query: str = Query(..., description="User question or search query"),
    db: Session = Depends(get_db),
):
    return _run_search(query, db)


@router.post(
    "/search",
    summary="Semantic product search with RAG + KG + LLM-aware ranking",
)
def search_products_post(
    body: SearchRequest,
    db: Session = Depends(get_db),
):
    """
    POST variant so the frontend can send JSON: { "query": "hoodies under 2000" }.
    """
    return _run_search(body.query, db)
