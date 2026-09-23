from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./resume_agent.db"
    UPLOAD_DIR: str = "./uploads"
    GENERATED_DIR: str = "./generated"
    OLLAMA_MODEL: str = "qwen2.5:14b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_MODEL: str = ""
    OPENAI_BASE_URL: str = ""

    # JWT 相关
    SECRET_KEY: str = "4f8a3c9b2e1d7a0f6e5c8b3a1d9e2f4a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # 使用 SettingsConfigDict 配置 .env 文件
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # 如果 .env 里有 Settings 未定义的额外变量，直接忽略不报错
    )

@lru_cache()
def get_settings():
    return Settings()