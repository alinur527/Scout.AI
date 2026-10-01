from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/scoutai.db"
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=120, ge=1, le=10080)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    upload_dir: Path = Path("data/uploads")
    model_weights: Path = Path("weights/yolo11n-pose.pt")
    demo_mode: bool = Field(default=False, validation_alias=AliasChoices("SCOUTAI_DEMO_MODE", "DEMO_MODE"))
    max_upload_mb: int = Field(default=200, ge=1, le=2000)
    max_video_seconds: int = Field(default=1800, ge=1, le=10800)
    max_video_frames: int = Field(default=54000, ge=1, le=324000)
    job_retention_days: int = Field(default=7, ge=1)

    @field_validator("jwt_algorithm")
    @classmethod
    def supported_algorithm(cls, value):
        if value != "HS256":
            raise ValueError("Only HS256 is supported")
        return value

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, value):
        if "*" in value:
            raise ValueError("CORS_ORIGINS must contain explicit origins")
        return value
