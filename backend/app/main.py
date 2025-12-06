# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import health, products, search, scrape


from app.core.config import settings
from app.api.v1 import health, products, search
from app.db.session import SessionLocal
from app.services.embeddings import index_all_products
from app.services.graph import sync_products_to_graph
from app.models.product import Product


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        redirect_slashes=False,
        version="0.1.0",
    )

    # ---------- CORS ----------
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- v1 routes ----------
    prefix = settings.API_V1_PREFIX  # should be "/api/v1"
    app.include_router(health.router, prefix=prefix)
    app.include_router(products.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(scrape.router, prefix=prefix)

    # ---------- global error handler ----------
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # TODO: log exc in real app
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # ---------- startup ----------
    @app.on_event("startup")
    def startup_index_qdrant_and_kg():
        print("🪄 Starting up — syncing embeddings & knowledge graph...")
        db = SessionLocal()
        try:
            # 1) Qdrant embeddings (runs only if empty)
            emb_chunks = index_all_products(db, skip_if_indexed=True)

            # 2) Neo4j KG (also only once, if no Product nodes)
            products = db.query(Product).all()
            kg_nodes = sync_products_to_graph(products, skip_if_exists=True)

            print(
                f"✨ Embedding chunks indexed (new): {emb_chunks}, "
                f"KG products synced (new): {kg_nodes}"
            )
        except Exception as e:
            print("❌ Error during startup embedding/KG sync:", e)
        finally:
            db.close()

    return app


app = create_app()
