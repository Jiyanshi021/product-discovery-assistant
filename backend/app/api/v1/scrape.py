# app/api/v1/scrape.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.scraper import scrape_hunnit_to_db

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeResponse(BaseModel):
    status: str
    collections: list[str]
    products_scraped: int
    created: int
    updated: int


@router.post("/hunnit", response_model=ScrapeResponse)
def scrape_hunnit(max_products: int = 40, db: Session = Depends(get_db)):
    """
    Scrape multiple Hunnit collections (jackets/hoodies, topwear,
    bottomwear, co-ord sets, bestseller) and upsert into Neon DB.
    """
    try:
        total, created, updated, collections = scrape_hunnit_to_db(
            db,
            max_products=max_products,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SCRAPE_ERROR: {type(e).__name__}: {e}",
        )

    return ScrapeResponse(
        status="ok",
        collections=collections,
        products_scraped=total,
        created=created,
        updated=updated,
    )
