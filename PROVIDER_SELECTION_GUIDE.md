# Provider Selection Guide

This guide explains how to use the new provider selection functionality in the LangGraph-based text-to-SQL flow system. The system now supports multiple LLM providers with conversation context management.

## Overview

The system supports three LLM providers:
- **OpenAI**: Standard OpenAI API (GPT-4, GPT-3.5-turbo)
- **Bedrock**: AWS Bedrock service (Claude, Llama, etc.)
- **Custom**: Your internal LLM provider with conversation context

## Features

### 1. Provider Selection
- Choose LLM provider via `provider` parameter in API requests
- Automatic conversation context management for all providers
- Seamless switching between providers

### 2. Conversation Context
- Maintains conversation history across all providers
- Automatic context management and token limits
- Context clearing and retrieval capabilities

### 3. Flow Execution
- Dynamic flow determination using selected provider
- Direct flow execution with provider selection
- Error handling for provider-specific issues

## API Endpoints

### Main Chat Endpoint
```http
POST /chat
```

**Request Body:**
```json
{
  "message": "Generate a SQL query to find all employees",
  "session_id": "optional-session-id",
  "provider": "custom",  // "openai", "bedrock", or "custom"
  "system_prompt": "You are a SQL expert",
  "clear_context": false,
  "max_context_messages": 10
}
```

**Response:**
```json
{
  "response": "SELECT * FROM employees WHERE department = 'sales'",
  "session_id": "session-123",
  "conversation_id": "conv-456",
  "provider": "custom",
  "selected_flow": "text_to_sql",
  "planning": {
    "selected_flow": "text_to_sql",
    "reasoning": "User requested SQL generation",
    "available_flows": ["text_to_sql", "general_qa"]
  }
}
```

### Specific Flow Execution
```http
POST /flow/{flow_name}
```

**Request Body:**
```json
{
  "message": "Find all customers with purchases > $1000",
  "session_id": "optional-session-id",
  "provider": "custom",
  "system_prompt": "You are a SQL expert",
  "clear_context": false
}
```

### Conversation Management
```http
POST /conversation/context
POST /conversation/clear
```

## Provider Configuration

### 1. OpenAI Provider
```python
# Environment variables
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4
PROVIDER=openai
```

### 2. Bedrock Provider
```python
# Environment variables
BEDROCK_REGION=us-east-1
BEDROCK_ACCESS_KEY=your-access-key
BEDROCK_SECRET_KEY=your-secret-key
BEDROCK_LLM_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
PROVIDER=bedrock
```

### 3. Custom Provider
```python
# Environment variables
CUSTOM_BASE_URL=https://your-llm-endpoint.com
CUSTOM_TENANT_ID=your-tenant-id
PROVIDER=custom
```

## Usage Examples

### Python Client Example

```python
import requests

# Send chat request with custom provider
def chat_with_custom_provider(message, session_id=None):
    url = "http://localhost:8000/chat"
    
    payload = {
        "message": message,
        "provider": "custom",
        "system_prompt": "You are a helpful SQL assistant"
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    response = requests.post(url, json=payload)
    return response.json()

# Execute specific flow with Bedrock
def execute_flow_with_bedrock(flow_name, message):
    url = f"http://localhost:8000/flow/{flow_name}"
    
    payload = {
        "message": message,
        "provider": "bedrock",
        "system_prompt": f"You are an expert in {flow_name}"
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# Get conversation context
def get_context(session_id):
    url = "http://localhost:8000/conversation/context"
    
    payload = {
        "session_id": session_id,
        "max_messages": 10
    }
    
    response = requests.post(url, json=payload)
    return response.json()
```

### JavaScript/TypeScript Example

```typescript
interface ChatRequest {
  message: string;
  session_id?: string;
  provider: 'openai' | 'bedrock' | 'custom';
  system_prompt?: string;
  clear_context?: boolean;
}

interface ChatResponse {
  response: string;
  session_id: string;
  conversation_id?: string;
  provider: string;
  selected_flow?: string;
  planning?: any;
}

async function sendChatRequest(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  return response.json();
}

// Usage
const result = await sendChatRequest({
  message: "Generate SQL to find high-value customers",
  provider: "custom",
  system_prompt: "You are a SQL expert"
});
```

## Custom LLM Integration

### Your Custom LLM Connector

The system integrates with your existing `LLMApi` class:

```python
class LLMApi:
    def __init__(self, tenant_id, token, token_expiry=None):
        self.base_url = settings.custom_base_url
        self.tenant_id = settings.custom_tenant_id
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.deployments = self.fetch_deployments()
    
    def invoke(self, message, deployment_id="text_to_sql", conversation_id=None):
        # Your existing implementation
        pass
```

### Contextual Integration

The system wraps your LLM with conversation context:

```python
class ContextualCustomLLMService:
    def invoke_with_context(
        self, 
        session_id: str, 
        user_message: str, 
        system_prompt: Optional[str] = None,
        deployment_id: str = "text_to_sql"
    ) -> Tuple[str, Optional[str]]:
        # Adds conversation context to your LLM calls
        # Manages conversation history automatically
        pass
```

## Configuration

### Environment Variables

Create a `.env` file:

```env
# Provider Selection
PROVIDER=custom

# OpenAI Configuration
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4

# Bedrock Configuration
BEDROCK_REGION=us-east-1
BEDROCK_ACCESS_KEY=your-access-key
BEDROCK_SECRET_KEY=your-secret-key
BEDROCK_LLM_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Custom LLM Configuration
CUSTOM_BASE_URL=https://your-llm-endpoint.com
CUSTOM_TENANT_ID=your-tenant-id

# Application Settings
APP_NAME="LangGraph Provider Demo"
DEBUG=true
MAX_ITERATIONS=10
```

### Settings Class

The system uses Pydantic settings for configuration:

```python
class Settings(BaseSettings):
    provider: str = "openai"
    openai_api_key: SecretStr
    openai_model: str = "gpt-4"
    bedrock_region: Optional[str] = None
    bedrock_access_key: Optional[SecretStr] = None
    bedrock_secret_key: Optional[SecretStr] = None
    bedrock_llm_model_id: Optional[str] = None
    custom_base_url: Optional[str] = None
    custom_tenant_id: Optional[str] = None
```

## Error Handling

### Provider-Specific Errors

```python
# Handle provider unavailability
try:
    result = send_chat_request(message, provider="custom")
except Exception as e:
    # Fallback to different provider
    result = send_chat_request(message, provider="openai")
```

### Common Error Responses

```json
{
  "error": "LLM provider 'invalid_provider' not available"
}
```

```json
{
  "error": "Flow 'non_existent_flow' not found"
}
```

## Best Practices

### 1. Provider Selection
- Use `custom` for internal/enterprise LLMs
- Use `bedrock` for AWS-managed models
- Use `openai` for general-purpose tasks

### 2. Session Management
- Reuse session IDs for continuous conversations
- Clear context when starting new topics
- Monitor context size to avoid token limits

### 3. Error Handling
- Implement fallback providers
- Handle provider-specific errors gracefully
- Log provider usage for monitoring

### 4. Performance
- Use appropriate deployment IDs for custom provider
- Monitor response times per provider
- Cache frequently used responses

## Monitoring and Debugging

### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "app_name": "LangGraph Provider Demo",
  "provider": "custom",
  "debug": true
}
```

### Conversation Context
```http
POST /conversation/context
```

Use this to debug conversation state and context management.

## Migration Guide

### From Single Provider to Multi-Provider

1. **Update API calls** to include `provider` parameter
2. **Configure environment variables** for desired providers
3. **Test with different providers** using the example script
4. **Update error handling** to handle provider-specific issues

### Example Migration

**Before:**
```python
response = requests.post("/chat", json={
    "message": "Generate SQL query"
})
```

**After:**
```python
response = requests.post("/chat", json={
    "message": "Generate SQL query",
    "provider": "custom",
    "session_id": "user-123"
})
```

## Troubleshooting

### Common Issues

1. **Provider not available**
   - Check environment variables
   - Verify API keys and credentials
   - Check network connectivity

2. **Conversation context issues**
   - Verify session ID consistency
   - Check context size limits
   - Clear context if needed

3. **Flow execution errors**
   - Verify flow exists in registry
   - Check provider compatibility
   - Review error logs

### Debug Commands

```bash
# Check API health
curl http://localhost:8000/health

# Test provider selection
python example_provider_selection.py

# Check conversation context
curl -X POST http://localhost:8000/conversation/context \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session"}'
```

## Conclusion

The provider selection system provides flexible LLM integration with conversation context management. It supports your custom LLM connector while maintaining compatibility with standard providers like OpenAI and Bedrock.

For more examples and advanced usage, see the `example_provider_selection.py` script. 