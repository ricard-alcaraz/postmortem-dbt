# src/postmortem_dbt/core/client.py
import httpx
from pydantic_settings import BaseSettings
from openai import OpenAI

class LLMSettings(BaseSettings):
    """Configuration for the LLM provider."""
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
    model: str = "google/gemma-4-12b"
    # Separate timeouts: connect is fast, read is long for generation
    connect_timeout: float = 10.0
    read_timeout: float = 300.0  # 5 minutes for local models
    max_retries: int = 2

    class Config:
        env_prefix = "LLM_"
        env_file = ".env"
        env_file_encoding = "utf-8"

class LLMClient:
    """Encapsulates the OpenAI client with proper timeouts for local models."""
    def __init__(self):
        self.settings = LLMSettings()
        
        # Use httpx.Timeout for granular control
        timeout = httpx.Timeout(
            connect=self.settings.connect_timeout,
            read=self.settings.read_timeout,
            write=self.settings.connect_timeout,
            pool=self.settings.connect_timeout,
        )
        
        self._client = OpenAI(
            base_url=self.settings.base_url,
            api_key=self.settings.api_key,
            timeout=timeout,
            max_retries=self.settings.max_retries,
        )

    def get_client(self) -> OpenAI:
        return self._client

    def get_model(self) -> str:
        return self.settings.model