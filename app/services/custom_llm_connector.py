import requests
from typing import List, Dict, Any, Optional
from ..core.config import settings

class CustomLLMConnector:
    """
    Connector for a custom internal LLM provider with API endpoints for invoke, token generation, and conversation management.
    """
    def __init__(self):
        self.base_url = settings.custom_base_url or "http://mock-custom-llm.local"
        self.invoke_endpoint = settings.custom_invoke_endpoint or "/api/invoke"
        self.token_endpoint = settings.custom_token_endpoint or "/api/token"
        self.conversation_endpoint = settings.custom_conversation_endpoint or "/api/conversation"
        self.api_key = settings.custom_api_key or "mock-api-key"

    def generate_token(self) -> str:
        """Obtain an access token from the custom provider (mock implementation)."""
        url = f"{self.base_url}{self.token_endpoint}"
        response = requests.post(url, json={"api_key": self.api_key})
        if response.status_code == 200:
            return response.json().get("token", "mock-token")
        else:
            raise Exception(f"Token generation failed: {response.text}")

    def invoke(self, messages: List[Dict[str, Any]], token: Optional[str] = None) -> str:
        """Invoke the LLM with a list of messages (mock implementation)."""
        url = f"{self.base_url}{self.invoke_endpoint}"
        headers = {"Authorization": f"Bearer {token or self.generate_token()}"}
        payload = {"messages": messages}
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("content", "mock-response")
        else:
            raise Exception(f"LLM invoke failed: {response.text}")

    def start_conversation(self, initial_message: str, token: Optional[str] = None) -> Dict[str, Any]:
        """Start a new conversation (mock implementation)."""
        url = f"{self.base_url}{self.conversation_endpoint}/start"
        headers = {"Authorization": f"Bearer {token or self.generate_token()}"}
        payload = {"initial_message": initial_message}
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Start conversation failed: {response.text}")

    def get_conversation(self, conversation_id: str, token: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve conversation history (mock implementation)."""
        url = f"{self.base_url}{self.conversation_endpoint}/{conversation_id}"
        headers = {"Authorization": f"Bearer {token or self.generate_token()}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Get conversation failed: {response.text}") 