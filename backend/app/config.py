from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os


class Settings(BaseSettings):
    # API Configuration
    app_name: str = "Document AI MVP"
    version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", 8000))
    
    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    
    # File Upload Settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_dir: str = "uploads"
    allowed_extensions: Union[List[str], str] = "pdf,png,jpg,jpeg,tiff,webp"
    
    # CORS Settings
    cors_origins: Union[List[str], str] = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600  # 1 hour
    
    # Processing Settings
    max_concurrent_processes: int = 5
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    @field_validator('allowed_extensions', 'cors_origins', mode='before')
    @classmethod
    def parse_comma_separated(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


settings = Settings()
