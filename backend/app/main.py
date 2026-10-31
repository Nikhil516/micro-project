from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import ROOT, settings
from app.database import connect, disconnect
from app.routes import analytics, auth, forecasts, model, products, reports, sales


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield
    await disconnect()


app = FastAPI(
    title="Fashion Demand Forecasting API",
    version="1.0.0",
    description="Multimodal weekly demand forecasting for fashion products.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(forecasts.router)
app.include_router(analytics.router)
app.include_router(model.router)
app.include_router(reports.router)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
catalog_dir = ROOT / "ml" / "datasets" / "images"
if catalog_dir.exists():
    app.mount("/catalog-images", StaticFiles(directory=catalog_dir), name="catalog_images")


@app.get("/health")
async def health():
    from app.ml.predictor import forecast_service

    return {
        "status": "ok",
        "database": settings.database_name,
        "model": forecast_service.status,
    }
