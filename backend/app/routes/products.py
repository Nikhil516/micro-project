from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pymongo import ReturnDocument

from app.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services.storage import save_image

router = APIRouter(prefix="/api/products", tags=["products"])


def _out(doc) -> ProductOut:
    return ProductOut(
        product_id=doc["product_id"],
        name=doc.get("name") or doc["product_id"],
        category=doc.get("category", "unknown"),
        colour=doc.get("colour", "unknown"),
        pattern=doc.get("pattern", "solid"),
        sleeve_type=doc.get("sleeve_type", "unknown"),
        description=doc.get("description", ""),
        image_url=doc.get("image_url"),
        has_history=bool(doc.get("has_history")),
        created_at=doc.get("created_at"),
    )


@router.get("", response_model=list[ProductOut])
async def list_products(user=Depends(get_current_user)):
    db = get_db()
    items = await db.products.find().sort("created_at", -1).to_list(2000)
    return [_out(i) for i in items]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str, user=Depends(get_current_user)):
    doc = await get_db().products.find_one({"product_id": product_id})
    if not doc:
        raise HTTPException(404, "Product not found")
    return _out(doc)


@router.post("", response_model=ProductOut)
async def create_product(body: ProductCreate, user=Depends(require_roles("admin", "analyst"))):
    db = get_db()
    product_id = body.product_id or f"sku_{uuid4().hex[:10]}"
    if await db.products.find_one({"product_id": product_id}):
        raise HTTPException(status.HTTP_409_CONFLICT, "product_id exists")
    doc = {
        **body.model_dump(),
        "product_id": product_id,
        "has_history": False,
        "created_at": datetime.now(timezone.utc),
        "created_by": user["email"],
    }
    await db.products.insert_one(doc)
    await db.inventory.update_one(
        {"product_id": product_id},
        {"$setOnInsert": {"on_hand": 0, "reorder_point": 10}},
        upsert=True,
    )
    return _out(doc)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(product_id: str, body: ProductUpdate, user=Depends(require_roles("admin", "analyst"))):
    db = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    result = await db.products.find_one_and_update(
        {"product_id": product_id}, {"$set": updates}, return_document=ReturnDocument.AFTER
    )
    if not result:
        raise HTTPException(404, "Product not found")
    return _out(result)


@router.delete("/{product_id}")
async def delete_product(product_id: str, user=Depends(require_roles("admin"))):
    result = await get_db().products.delete_one({"product_id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Product not found")
    return {"message": "Deleted"}


@router.post("/{product_id}/image", response_model=ProductOut)
async def upload_image(
    product_id: str,
    file: UploadFile = File(...),
    user=Depends(require_roles("admin", "analyst")),
):
    db = get_db()
    doc = await db.products.find_one({"product_id": product_id})
    if not doc:
        raise HTTPException(404, "Product not found")
    url = await save_image(file)
    updated = await db.products.find_one_and_update(
        {"product_id": product_id},
        {"$set": {"image_url": url}},
        return_document=ReturnDocument.AFTER,
    )
    return _out(updated)
