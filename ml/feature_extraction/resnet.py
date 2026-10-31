"""Pretrained ResNet-50 (ImageNet) embeddings with global average pooling."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, UnidentifiedImageError

from ml.preprocessing.paths import IMAGE_DIR, MODELS_DIR, PROCESSED_DIR, ROOT, ensure_dirs

IMG_SIZE = (224, 224)
EMBED_DIM = 2048


def _load_resnet():
    import tensorflow as tf
    from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input

    tf.keras.backend.clear_session()
    model = ResNet50(weights="imagenet", include_top=False, pooling="avg")
    model.trainable = False
    return model, preprocess_input


def preprocess_image(path: Path, preprocess_input):
    try:
        with Image.open(path) as img:
            img = img.convert("RGB").resize(IMG_SIZE)
            arr = np.asarray(img, dtype=np.float32)
    except (UnidentifiedImageError, OSError):
        return None
    arr = np.expand_dims(arr, axis=0)
    return preprocess_input(arr)


def extract_embeddings(image_limit: int | None = None, batch_size: int = 16) -> Path:
    ensure_dirs()
    products = pd.read_csv(PROCESSED_DIR / "products.csv")
    if image_limit:
        n_cat = max(1, products["category"].nunique())
        per = max(1, image_limit // n_cat)
        products = products.groupby("category", group_keys=False).head(per)

    model, preprocess_input = _load_resnet()
    embeddings = []
    valid_ids = []
    failed = []
    batch_imgs = []
    batch_ids = []

    def flush():
        nonlocal batch_imgs, batch_ids
        if not batch_imgs:
            return
        x = np.concatenate(batch_imgs, axis=0)
        preds = model.predict(x, verbose=0)
        embeddings.append(preds)
        valid_ids.extend(batch_ids)
        batch_imgs, batch_ids = [], []

    for row in products.itertuples(index=False):
        path = ROOT / row.image_path
        if not path.exists():
            fallback = IMAGE_DIR / Path(row.image_path).name
            path = fallback if fallback.exists() else path
        arr = preprocess_image(path, preprocess_input)
        if arr is None:
            failed.append(row.product_id)
            continue
        batch_imgs.append(arr)
        batch_ids.append(row.product_id)
        if len(batch_imgs) >= batch_size:
            flush()
    flush()

    if not embeddings:
        raise RuntimeError("No image embeddings were generated")

    matrix = np.vstack(embeddings)
    out_npy = MODELS_DIR / "resnet50_embeddings.npy"
    ids_path = MODELS_DIR / "resnet50_product_ids.json"
    np.save(out_npy, matrix)
    ids_path.write_text(json.dumps(valid_ids))
    table = pd.DataFrame(matrix, columns=[f"img_{i}" for i in range(matrix.shape[1])])
    table.insert(0, "product_id", valid_ids)
    table.to_parquet(PROCESSED_DIR / "image_embeddings.parquet", index=False)

    meta = {
        "architecture": "ResNet50",
        "weights": "imagenet",
        "include_top": False,
        "pooling": "avg",
        "image_size": list(IMG_SIZE),
        "embedding_dim": int(matrix.shape[1]),
        "n_embedded": int(matrix.shape[0]),
        "n_failed": len(failed),
        "failed_product_ids": failed[:50],
        "fine_tuned": False,
    }
    (MODELS_DIR / "resnet50_config.json").write_text(json.dumps(meta, indent=2))
    return out_npy


def embed_single(image_path: str | Path) -> np.ndarray:
    model, preprocess_input = _load_resnet()
    arr = preprocess_image(Path(image_path), preprocess_input)
    if arr is None:
        raise ValueError(f"Could not read image: {image_path}")
    return model.predict(arr, verbose=0)[0]


if __name__ == "__main__":
    print(extract_embeddings())
