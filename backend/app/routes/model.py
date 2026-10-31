from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.middleware.auth import get_current_user
from app.ml.predictor import forecast_service
from pathlib import Path

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/info")
async def info(user=Depends(get_current_user)):
    return forecast_service.model_info()


@router.get("/test-predictions")
async def test_predictions(user=Depends(get_current_user)):
    path = Path(settings.model_dir) / "test_predictions.csv"
    if not path.exists():
        raise HTTPException(404, "No evaluation prediction file. Train the model first.")
    return FileResponse(path, filename="test_predictions.csv")
