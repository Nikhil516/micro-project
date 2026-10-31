"""Single entry point for the offline ML pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-limit", type=int, default=180, help="Cap images for CPU ResNet-50 (college default)")
    parser.add_argument("--skip-acquire", action="store_true")
    args = parser.parse_args()

    from ml.preprocessing.acquire import acquire
    from ml.preprocessing.clean import preprocess
    from ml.feature_extraction.resnet import extract_embeddings
    from ml.training.train import smoke_predict, train_xgb
    from ml.preprocessing.paths import PROCESSED_DIR

    if not args.skip_acquire or not (PROCESSED_DIR / "products.csv").exists():
        acquire()
    preprocess()
    extract_embeddings(image_limit=args.image_limit)
    metrics = train_xgb(image_limit=args.image_limit)
    smoke = smoke_predict()
    print(json.dumps({"metrics": metrics, "smoke_predict": smoke}, indent=2, default=str))


if __name__ == "__main__":
    main()
