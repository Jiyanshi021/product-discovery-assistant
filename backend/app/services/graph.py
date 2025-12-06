# app/services/graph.py
from typing import List, Dict, Any

from neo4j import GraphDatabase, Driver

from app.core.config import settings
from app.models.product import Product

_driver: Driver | None = None


def get_neo4j_driver() -> Driver:
    """
    Get (and lazily create) a Neo4j driver.

    If NEO4J_ENABLED is False this should normally not be called; callers
    are expected to short-circuit before.
    """
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


# ---- schema helpers (indexes optional, no UNIQUE constraints) ----


def ensure_schema() -> None:
    """
    For this assignment we keep it simple:
    - no UNIQUE constraints (they were causing SchemaConstraintValidationFailed)
    - optionally create normal indexes (not required for correctness)
    """
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            # Non-unique indexes (safe even if data is messy)
            session.run(
                "CREATE INDEX product_id_index IF NOT EXISTS "
                "FOR (p:Product) ON (p.product_id)"
            )
            session.run(
                "CREATE INDEX category_name_index IF NOT EXISTS "
                "FOR (c:Category) ON (c.name)"
            )
            session.run(
                "CREATE INDEX feature_name_index IF NOT EXISTS "
                "FOR (f:Feature) ON (f.name)"
            )
    except Exception as e:
        # Index creation failure should never break app startup
        print("⚠️ Skipping Neo4j index creation due to error:", e)


# ---- core write helpers ----


def _upsert_product_tx(
    tx,
    product_id: int,
    title: str | None,
    category: str | None,
    price: float | None,
    features: List[str],
):
    tx.run(
        """
        MERGE (p:Product {product_id: $product_id})
        SET p.title = $title,
            p.category = $category,
            p.price = $price
        """,
        product_id=product_id,
        title=title,
        category=category,
        price=price,
    )

    if category:
        tx.run(
            """
            MERGE (c:Category {name: $category})
            MERGE (p:Product {product_id: $product_id})-[:BELONGS_TO]->(c)
            """,
            product_id=product_id,
            category=category,
        )

    for feat in features:
        tx.run(
            """
            MERGE (f:Feature {name: $name})
            MERGE (p:Product {product_id: $product_id})-[:HAS_FEATURE]->(f)
            """,
            name=feat,
            product_id=product_id,
        )


def _count_products_tx(tx) -> int:
    record = tx.run("MATCH (p:Product) RETURN count(p) AS c").single()
    return int(record["c"]) if record else 0


def _delete_kg_tx(tx):
    """
    (Currently unused)
    Delete current KG for this app only:
    - all Product nodes
    - any Category/Feature nodes that become orphan.
    """
    # delete all Product nodes + attached relationships
    tx.run("MATCH (p:Product) DETACH DELETE p")
    # clean up orphan categories/features (no remaining relationships)
    tx.run(
        """
        MATCH (c:Category)
        WHERE NOT (c)--()
        DELETE c
        """
    )
    tx.run(
        """
        MATCH (f:Feature)
        WHERE NOT (f)--()
        DELETE f
        """
    )


# ---- public sync + read APIs ----


def sync_products_to_graph(
    products: List[Product],
    skip_if_exists: bool = True,
) -> int:
    """
    Push products into Neo4j as a small knowledge graph.

    New behaviour (to avoid expensive rebuilds):
    - If NEO4J_ENABLED=False  → skip completely.
    - If no products in DB     → skip.
    - If ANY Product nodes already exist in Neo4j AND skip_if_exists=True
        → assume graph is already prepared, SKIP (no rebuild, no delete).
    - Otherwise:
        → only upsert products (MERGE) without deleting existing graph.
    """
    if not settings.NEO4J_ENABLED:
        print("ℹ️ Neo4j disabled (NEO4J_ENABLED=False) — skipping KG sync.")
        return 0

    if not products:
        return 0

    driver = get_neo4j_driver()
    ensure_schema()

    with driver.session() as session:
        existing = session.execute_read(_count_products_tx)

        # 🔹 IMPORTANT CHANGE:
        # Agar graph me already koi Product nodes hain aur hum skip_if_exists=True
        # use kar rahe hain (startup case), to direct skip kar do — mismatch
        # check ya rebuild nahi hoga.
        if skip_if_exists and existing > 0:
            print(
                f"ℹ️ Existing Neo4j KG detected "
                f"(Product nodes: {existing}) — skipping KG sync."
            )
            return 0

        # Agar skip_if_exists=False diya hai, to soft upsert karega
        # (NO delete, NO full rebuild) — sirf MERGE.
        upserted = 0
        for p in products:
            if isinstance(p.features, dict):
                feats = [f"{k}: {v}" for k, v in p.features.items()]
            elif isinstance(p.features, list):
                feats = [str(x) for x in p.features]
            elif isinstance(p.features, str):
                feats = [f.strip() for f in p.features.split(",") if f.strip()]
            else:
                feats = []

            price_val = float(p.price) if p.price is not None else None

            session.execute_write(
                _upsert_product_tx,
                p.id,
                p.title,
                p.category,
                price_val,
                feats,
            )
            upserted += 1

    return upserted


def get_candidate_product_ids_from_kg(
    category_hint: str | None,
    max_price: float | None,
    tags: List[str],
) -> List[int]:
    """
    Use Neo4j as a conceptual filter:
    - category_hint: e.g. "hoodie", "tshirt"
    - max_price: e.g. 2000
    - tags: style / intent words like ["oversized", "winter", "casual"]

    Returns a list of product_ids that match these constraints.
    If Neo4J is disabled or no matches, returns [].
    """
    if not settings.NEO4J_ENABLED:
        return []

    driver = get_neo4j_driver()
    tags = [t.lower() for t in tags if t]

    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Product)
            OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
            OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
            WITH p, c, f
            WHERE
              (
                $category IS NULL
                OR toLower(p.category) CONTAINS $category
                OR (c IS NOT NULL AND toLower(c.name) CONTAINS $category)
              )
              AND
              (
                $max_price IS NULL
                OR p.price IS NULL
                OR p.price <= $max_price
              )
              AND
              (
                size($tags) = 0 OR
                any(t IN $tags WHERE
                    (f IS NOT NULL AND toLower(f.name) CONTAINS t) OR
                    toLower(p.title) CONTAINS t OR
                    toLower(coalesce(p.description, "")) CONTAINS t
                )
              )
            RETURN DISTINCT p.product_id AS id
            """,
            category=(category_hint.lower() if category_hint else None),
            max_price=max_price,
            tags=tags,
        )

        ids: List[int] = [rec["id"] for rec in result if rec.get("id") is not None]
        return ids


def get_kg_context_for_products(product_ids: List[int]) -> List[str]:
    """
    For given product_ids, return human-readable KG context strings
    (categories + features) that we can feed into the LLM with RAG.

    Returns [] when NEO4J_ENABLED=False or product_ids empty.
    """
    if not settings.NEO4J_ENABLED:
        return []

    if not product_ids:
        return []

    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Product)
            WHERE p.product_id IN $ids
            OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
            OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
            RETURN p.product_id AS id,
                   p.title AS title,
                   collect(DISTINCT c.name) AS categories,
                   collect(DISTINCT f.name) AS features
            """,
            ids=product_ids,
        )

        contexts: List[str] = []
        for record in result:
            title = record["title"] or ""
            cats = [c for c in record["categories"] if c]
            feats = [f for f in record["features"] if f]

            text = (
                f"Product: {title}\n"
                f"Categories: {', '.join(cats) if cats else 'N/A'}\n"
                f"Features: {', '.join(feats) if feats else 'N/A'}"
            )
            contexts.append(text)

        return contexts
