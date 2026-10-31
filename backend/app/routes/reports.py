import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.database import get_db
from app.middleware.auth import get_current_user
from app.ml.predictor import forecast_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/forecasts.csv")
async def forecasts_csv(user=Depends(get_current_user)):
    rows = await get_db().forecasts.find().sort("created_at", -1).to_list(2000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["product_id", "week_start", "predicted_units", "cold_start", "model_version", "created_at"])
    for row in rows:
        for step in row.get("forecasts") or []:
            writer.writerow(
                [
                    row.get("product_id"),
                    step.get("week_start"),
                    step.get("predicted_units"),
                    row.get("cold_start"),
                    row.get("model_version"),
                    row.get("created_at"),
                ]
            )
    data = buf.getvalue().encode()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=forecasts.csv"},
    )


@router.get("/forecasts.pdf")
async def forecasts_pdf(user=Depends(get_current_user)):
    rows = await get_db().forecasts.find().sort("created_at", -1).to_list(30)
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle("Weekly demand forecast report")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 800, "Fashion Demand Forecast Report")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, 782, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    info = forecast_service.model_info()
    pdf.drawString(40, 766, f"Model: {info.get('model_version')}  status={info.get('status')}")
    metrics = info.get("metrics") or {}
    pdf.drawString(
        40,
        750,
        f"Hold-out MAE={metrics.get('mae')}  RMSE={metrics.get('rmse')}  WAPE={metrics.get('wape')}",
    )
    y = 720
    for row in rows:
        line = f"{row.get('product_id')}  cold_start={row.get('cold_start')}"
        pdf.drawString(40, y, line[:110])
        y -= 14
        for step in (row.get("forecasts") or [])[:4]:
            pdf.drawString(60, y, f"{step.get('week_start')}: {step.get('predicted_units')} units")
            y -= 12
            if y < 60:
                pdf.showPage()
                y = 800
        y -= 6
        if y < 60:
            pdf.showPage()
            y = 800
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=forecasts.pdf"},
    )
