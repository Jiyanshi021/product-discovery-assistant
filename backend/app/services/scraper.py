# app/services/scraper.py

from typing import Dict, Tuple, List
from datetime import datetime

from fastapi import HTTPException as FastAPIHTTPException
from sqlalchemy.orm import Session

from Data_Scraping.scrap import (
    get_product_links_from_collection,
    parse_hunnit_product,
    HUNNIT_COLLECTION_URL,
)
from app.models.product import Product


# All collections we want to scrape
HUNNIT_COLLECTIONS: List[tuple[str, str]] = [
    ("Bestseller", HUNNIT_COLLECTION_URL),
    ("Jackets & Hoodies", "https://hunnit.com/collections/jackets-hoodies"),
    ("Bottomwear", "https://hunnit.com/collections/all-bottomwear"),
    ("Topwear", "https://hunnit.com/collections/all-topwear"),
    ("Co-ord Set", "https://hunnit.com/collections/co-ord-set"),
]


def scrape_hunnit_to_db(
    db: Session,
    max_products: int = 40,
) -> Tuple[int, int, int, str]:
    """
    Scrape multiple Hunnit collections and upsert into PostgreSQL.

    - max_products -> per collection (e.g. 40 => each of 5 collections, total ≈ 200)
    - Existing products are preserved (no TRUNCATE)
    - Uses Product.product_url as the unique key for upsert

    Returns:
        total_scraped, created, updated, (primary) collection_url
    """

    total_created = 0
    total_updated = 0
    total_skipped = 0

    for category_name, collection_url in HUNNIT_COLLECTIONS:
        print(f"⚡ Scraping collection: {category_name} -> {collection_url}")

        try:
            links = get_product_links_from_collection(
                collection_url=collection_url,
                max_products=max_products,
            )
        except FastAPIHTTPException as e:
            print(f"[SCRAPE SKIP COLLECTION] {collection_url} -> {e.detail}")
            continue

        for url in links:
            try:
                product_data: Dict = parse_hunnit_product(
                    url,
                    category=category_name,
                )
            except FastAPIHTTPException as e:
                print(f"[SCRAPE SKIP] {url} -> {e.detail}")
                total_skipped += 1
                continue
            except Exception as e:
                print(f"[SCRAPE ERROR] {url} -> {e}")
                total_skipped += 1
                continue

            if not product_data.get("title"):
                print(f"[SCRAPE SKIP] {url} -> missing title")
                total_skipped += 1
                continue

            now = datetime.utcnow()

            # Upsert based on product_url
            existing = (
                db.query(Product)
                .filter(Product.product_url == product_data["product_url"])
                .one_or_none()
            )

            if existing:
                existing.title = product_data.get("title")
                existing.price = product_data.get("price")
                existing.description = product_data.get("description")
                existing.features = product_data.get("features")
                existing.image_url = product_data.get("image_url")
                existing.category = product_data.get("category")
                if hasattr(existing, "updated_at"):
                    existing.updated_at = now
                total_updated += 1
            else:
                kwargs = dict(
                    title=product_data.get("title"),
                    price=product_data.get("price"),
                    description=product_data.get("description"),
                    features=product_data.get("features"),
                    image_url=product_data.get("image_url"),
                    category=product_data.get("category"),
                    product_url=product_data.get("product_url"),
                )
                if hasattr(Product, "created_at"):
                    kwargs["created_at"] = now
                if hasattr(Product, "updated_at"):
                    kwargs["updated_at"] = now

                new_p = Product(**kwargs)
                db.add(new_p)
                total_created += 1

        db.commit()

    total = total_created + total_updated

    if total == 0:
        raise FastAPIHTTPException(
            status_code=500, detail="No products parsed successfully"
        )

    print(
        f"[SCRAPE DONE] total={total}, created={total_created}, "
        f"updated={total_updated}, skipped={total_skipped}"
    )

    # API schema still expects single collection_url; use bestseller as primary
    return total, total_created, total_updated, HUNNIT_COLLECTION_URL
