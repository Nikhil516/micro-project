from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ML_DIR = ROOT / "ml"
DATA_DIR = ML_DIR / "datasets"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
IMAGE_DIR = DATA_DIR / "images"
MODELS_DIR = ML_DIR / "models"


def ensure_dirs() -> None:
    for path in (RAW_DIR, PROCESSED_DIR, IMAGE_DIR, MODELS_DIR):
        path.mkdir(parents=True, exist_ok=True)
