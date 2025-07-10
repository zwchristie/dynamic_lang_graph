from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Environment variables:
# - PROVIDER (openai|bedrock)
# - OPENAI_API_KEY
# - OPENAI_MODEL
# - BEDROCK_REGION
# - BEDROCK_ACCESS_KEY
# - BEDROCK_SECRET_KEY
# - BEDROCK_LLM_MODEL_ID
# - BEDROCK_EMBEDDING_MODEL_ID
# - DATABASE_URL
# - APP_NAME
# - DEBUG
# - MAX_ITERATIONS

class Settings(BaseSettings):
    provider: str = "openai"  # "openai" or "bedrock"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4"
    bedrock_region: Optional[str] = None
    bedrock_access_key: Optional[SecretStr] = None
    bedrock_secret_key: Optional[SecretStr] = None
    bedrock_llm_model_id: Optional[str] = None
    bedrock_embedding_model_id: Optional[str] = None
    database_url: str = "sqlite:///./app.db"
    app_name: str = "Agentic Workflow System"
    debug: bool = False
    max_iterations: int = 10
    # Custom LLM provider settings
    custom_base_url: Optional[str] = None
    custom_invoke_endpoint: Optional[str] = None
    custom_token_endpoint: Optional[str] = None
    custom_conversation_endpoint: Optional[str] = None
    custom_api_key: Optional[SecretStr] = None
    custom_tenant_id: Optional[str] = None

settings = Settings()