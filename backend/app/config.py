from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "fashion_forecasting"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 1440
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    weather_api_key: str = ""
    google_trends_configuration: str = ""
    frontend_url: str = "http://localhost:5173"
    model_dir: str = str(ROOT / "ml" / "models")
    upload_dir: str = str(Path(__file__).resolve().parents[1] / "uploads")


settings = Settings()
