# app/main.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import health, products, search, scrape
from app.db.session import SessionLocal
from app.services.embeddings import index_all_products


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # v1 routes
    prefix = settings.API_V1_PREFIX
    app.include_router(health.router, prefix=prefix)
    app.include_router(products.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(scrape.router, prefix=prefix)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # TODO: log exc in real app
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.on_event("startup")
    def startup_index_qdrant():
        # Render / production: skip heavy embedding work
        if os.getenv("RENDER_ENVIRONMENT") == "production":
            print("🪄 Startup: skipping embedding & KG sync (Render 512MB limit).")
            return

        # Local: Only index if Qdrant is empty
        print("🚀 Startup: checking Qdrant & indexing products only if empty...")
        db = SessionLocal()
        try:
            indexed = index_all_products(db, skip_if_indexed=True)
            print(f"✨ Qdrant sync complete — newly indexed: {indexed}")
        finally:
            db.close()

    return app


app = create_app()
