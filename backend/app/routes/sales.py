import csv
import io
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pymongo import ReturnDocument

from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.schemas.sales import SaleIn, WeeklySale

router = APIRouter(prefix="/api/sales", tags=["sales"])


def _serialize(doc):
    return {
        "id": str(doc["_id"]),
        "product_id": doc["product_id"],
        "date": doc["date"].isoformat() if hasattr(doc["date"], "isoformat") else str(doc["date"]),
        "quantity": doc["quantity"],
        "revenue": doc.get("revenue"),
        "created_at": doc.get("created_at"),
    }


@router.get("")
async def list_sales(
    product_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user=Depends(get_current_user),
):
    query = {}
    if product_id:
        query["product_id"] = product_id
    if start or end:
        query["date"] = {}
        if start:
            query["date"]["$gte"] = datetime.fromisoformat(start)
        if end:
            query["date"]["$lte"] = datetime.fromisoformat(end)
    rows = await get_db().sales.find(query).sort("date", -1).to_list(5000)
    return [_serialize(r) for r in rows]


@router.post("")
async def add_sale(body: SaleIn, user=Depends(require_roles("admin", "analyst"))):
    db = get_db()
    if not await db.products.find_one({"product_id": body.product_id}):
        raise HTTPException(404, "Product not found")
    doc = {
        **body.model_dump(),
        "date": datetime.combine(body.date, datetime.min.time()),
        "created_at": datetime.now(timezone.utc),
        "source": "manual",
    }
    result = await db.sales.insert_one(doc)
    await db.products.update_one({"product_id": body.product_id}, {"$set": {"has_history": True}})
    doc["_id"] = result.inserted_id
    return _serialize(doc)


@router.patch("/{sale_id}")
async def update_sale(sale_id: str, body: SaleIn, user=Depends(require_roles("admin", "analyst"))):
    try:
        oid = ObjectId(sale_id)
    except Exception as exc:
        raise HTTPException(400, "Invalid sale id") from exc
    updates = {
        "product_id": body.product_id,
        "date": datetime.combine(body.date, datetime.min.time()),
        "quantity": body.quantity,
        "revenue": body.revenue,
    }
    doc = await get_db().sales.find_one_and_update(
        {"_id": oid}, {"$set": updates}, return_document=ReturnDocument.AFTER
    )
    if not doc:
        raise HTTPException(404, "Sale not found")
    return _serialize(doc)


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), user=Depends(require_roles("admin", "analyst"))):
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    required = {"product_id", "date", "quantity"}
    if not reader.fieldnames or not required.issubset({f.strip() for f in reader.fieldnames}):
        raise HTTPException(400, "CSV must include product_id, date, quantity")
    db = get_db()
    inserted = 0
    errors = []
    for i, row in enumerate(reader, start=2):
        try:
            pid = row["product_id"].strip()
            if not await db.products.find_one({"product_id": pid}):
                errors.append({"row": i, "error": "unknown product"})
                continue
            doc = {
                "product_id": pid,
                "date": datetime.fromisoformat(row["date"].strip()),
                "quantity": float(row["quantity"]),
                "revenue": float(row["revenue"]) if row.get("revenue") else None,
                "created_at": datetime.now(timezone.utc),
                "source": "csv",
            }
            await db.sales.insert_one(doc)
            await db.products.update_one({"product_id": pid}, {"$set": {"has_history": True}})
            inserted += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": i, "error": str(exc)})
    return {"inserted": inserted, "errors": errors[:50]}


@router.get("/weekly", response_model=list[WeeklySale])
async def weekly(
    product_id: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    match = {}
    if product_id:
        match["product_id"] = product_id
    pipeline = [
        {"$match": match} if match else {"$match": {}},
        {
            "$group": {
                "_id": {
                    "product_id": "$product_id",
                    "week": {"$dateTrunc": {"date": "$date", "unit": "week", "startOfWeek": "monday"}},
                },
                "units": {"$sum": "$quantity"},
            }
        },
        {"$sort": {"_id.week": 1}},
        {"$limit": 5000},
    ]
    rows = await get_db().sales.aggregate(pipeline).to_list(5000)
    return [
        WeeklySale(
            product_id=r["_id"]["product_id"],
            week_start=r["_id"]["week"].date(),
            units=r["units"],
        )
        for r in rows
    ]
