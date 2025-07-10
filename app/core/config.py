from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import Optional
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment-specific .env file
env = os.getenv("ENVIRONMENT", "local")
env_file = f".env.{env}"
if Path(env_file).exists():
    load_dotenv(env_file)
else:
    load_dotenv()  # Fallback to default .env

# Environment variables:
# - ENVIRONMENT (local|dev|testing)
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
# - SSL_CERT_FILE (for dev/testing)
# - SSL_KEY_FILE (for dev/testing)
# - HOST
# - PORT

class Settings(BaseSettings):
    # Environment
    environment: str = "local"
    
    # Provider settings
    provider: str = "openai"  # "openai" or "bedrock"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4"
    bedrock_region: Optional[str] = None
    bedrock_access_key: Optional[SecretStr] = None
    bedrock_secret_key: Optional[SecretStr] = None
    bedrock_llm_model_id: Optional[str] = None
    bedrock_embedding_model_id: Optional[str] = None
    
    # Database
    database_url: str = "sqlite:///./app.db"
    
    # App settings
    app_name: str = "Agentic Workflow System"
    debug: bool = False
    max_iterations: int = 10
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # SSL/TLS settings (for dev/testing environments)
    ssl_cert_file: Optional[str] = None
    ssl_key_file: Optional[str] = None
    
    # Custom LLM provider settings
    custom_base_url: Optional[str] = None
    custom_invoke_endpoint: Optional[str] = None
    custom_token_endpoint: Optional[str] = None
    custom_conversation_endpoint: Optional[str] = None
    custom_api_key: Optional[SecretStr] = None
    
    @property
    def use_ssl(self) -> bool:
        """Check if SSL should be used based on environment"""
        return (self.environment in ["dev", "testing"] and 
                self.ssl_cert_file is not None and 
                self.ssl_key_file is not None)
    
    @property
    def ssl_context(self) -> Optional[dict]:
        """Get SSL context for uvicorn if certificates are available"""
        if self.use_ssl and self.ssl_cert_file and self.ssl_key_file:
            cert_path = Path(self.ssl_cert_file)
            key_path = Path(self.ssl_key_file)
            
            if cert_path.exists() and key_path.exists():
                return {
                    "ssl_certfile": str(cert_path),
                    "ssl_keyfile": str(key_path)
                }
        return None

settings = Settings()