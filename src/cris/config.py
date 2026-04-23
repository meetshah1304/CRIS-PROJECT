from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env file relative to this file (src/cris/config.py → project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=_ENV_FILE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = Field(default="")
    supabase_key: str = Field(default="")
    supabase_schema: str = Field(default="public")
    embedding_model: str = Field(default="intfloat/multilingual-e5-small")
    fallback_embedding_model: str = Field(default="intfloat/multilingual-e5-small")
    ocr_engine: str = Field(default="tesseract")
    tesseract_cmd: str = Field(default=r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    data_dir: str = Field(default=str(_PROJECT_ROOT / "FIR Report 2022 to 2026"))
    processing_state_path: str = Field(default=str(_PROJECT_ROOT / ".cris" / "processing_state.json"))
    batch_history_path: str = Field(default=str(_PROJECT_ROOT / ".cris" / "batch_history.json"))
    huggingface_cache_dir: str = Field(default=str(_PROJECT_ROOT / ".cris" / "hf-cache"))
    embed_cache_dir: str = Field(default=str(_PROJECT_ROOT / ".cris" / "embed-cache"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
