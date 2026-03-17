from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# .env lives at project root (one level above this file's directory)
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    llm_provider: str = "groq"
    llm_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""

    database_url: str = "sqlite:///rfp_pipeline.db"

    usda_api_key: str = ""
    tavily_api_key: str = ""
    agentmail_api_key: str = ""
    agentmail_inbox: str = "rfp-agent@agentmail.to"

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
