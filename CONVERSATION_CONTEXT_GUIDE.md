# Conversation Context Management Guide

## Overview

The conversation context management system provides a robust solution for maintaining conversation history and context across multiple requests, even when your LLM endpoint doesn't provide context management. This system ensures that conversations remain coherent and contextually aware.

## Key Features

### 1. Persistent Conversation Storage
- Maintains conversation history per session
- Automatic message trimming to prevent memory issues
- Configurable message limits and token management

### 2. Context-Aware LLM Integration
- Automatically includes relevant conversation history in LLM requests
- Smart context truncation based on token limits
- System prompt integration with conversation context

### 3. Session Management
- Unique session IDs for each conversation
- Conversation persistence across requests
- Easy context clearing and restart capabilities

### 4. Token Management
- Automatic token estimation and usage tracking
- Configurable context window limits
- Smart context truncation to stay within limits

## Architecture

### Core Components

#### 1. ConversationManager (`app/services/conversation_manager.py`)
- Manages conversation storage and retrieval
- Handles message persistence and cleanup
- Provides context formatting for LLM

#### 2. ContextualLLMService (`app/services/contextual_llm_service.py`)
- Integrates conversation context with LLM calls
- Handles context-aware prompt generation
- Manages token limits and context truncation

#### 3. Enhanced Orchestrator (`app/services/orchestrator.py`)
- Uses contextual LLM service for flow determination
- Maintains conversation context across flow executions
- Provides conversation management endpoints

## Usage Examples

### Basic Conversation with Context

```python
from app.services.contextual_llm_service import contextual_llm_service

# Start a conversation
session_id = "user-123"

# First message
response1, conversation_id1 = contextual_llm_service.invoke_with_context(
    session_id=session_id,
    user_message="Hello, I need help with SQL queries"
)

# Follow-up message (context is automatically included)
response2, conversation_id2 = contextual_llm_service.invoke_with_context(
    session_id=session_id,
    user_message="Can you show me how to write a SELECT statement?"
)
```

### Using the API

```python
import requests

# Start a conversation
response = requests.post("http://localhost:8000/api/chat", json={
    "messages": [{"role": "user", "content": "Hello, I need SQL help"}],
    "session_id": "user-123"
})

# Follow-up (context is automatically maintained)
response = requests.post("http://localhost:8000/api/chat", json={
    "messages": [{"role": "user", "content": "Show me a SELECT query"}],
    "session_id": "user-123"  # Same session ID maintains context
})
```

### Getting Conversation Context

```python
# Get conversation summary
context = requests.get("http://localhost:8000/api/conversations/user-123")
print(context.json())

# Clear conversation context
requests.delete("http://localhost:8000/api/conversations/user-123")
```

## API Endpoints

### Conversation Management

1. **GET /api/conversations/{session_id}**
   - Get conversation context and summary
   - Returns message count, token usage, and recent messages

2. **DELETE /api/conversations/{session_id}**
   - Clear conversation context for a session
   - Useful for starting fresh conversations

### Enhanced Chat Endpoint

- **POST /api/chat** now automatically maintains conversation context
- Context is preserved across multiple requests with the same session_id
- No changes needed to existing chat requests

## Configuration

### Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4

# Context Management (optional)
MAX_CONTEXT_MESSAGES=50
MAX_CONTEXT_TOKENS=4000
```

### Service Configuration

```python
# In contextual_llm_service.py
class ContextualLLMService:
    def __init__(self):
        self.max_context_tokens = 4000  # Adjust based on your model
        self.max_context_messages = 50   # Maximum messages to keep
```

## Integration with Existing Flows

### Text-to-SQL Flow

The text-to-SQL flow now automatically benefits from conversation context:

```python
# User: "I have a users table"
# System: Generates SQL with context

# User: "Show me users who signed up this year"
# System: Uses previous context about the users table

# User: "Also include their email addresses"
# System: Modifies previous query with new requirements
```

### General QA Flow

General questions also maintain context:

```python
# User: "What is the capital of France?"
# System: Provides answer

# User: "Tell me more about its history"
# System: Uses context to provide relevant historical information
```

## Benefits

### 1. Improved User Experience
- Conversations feel natural and coherent
- No need to repeat context in each message
- Follow-up questions work seamlessly

### 2. Better LLM Performance
- Context helps LLM provide more relevant responses
- Reduces redundant information in prompts
- Improves accuracy for complex multi-step requests

### 3. Flexible Implementation
- Works with any LLM endpoint that doesn't maintain context
- Easy to integrate with existing systems
- Configurable for different use cases

## Advanced Features

### 1. Context Truncation

The system automatically manages context size:

```python
# Get context size information
context_size = contextual_llm_service.get_context_size(session_id)
print(f"Usage: {context_size['context_usage_percent']}%")
```

### 2. System Message Integration

Add system messages to conversations:

```python
# Add system prompt to conversation
contextual_llm_service.add_system_message(
    session_id="user-123",
    system_message="You are a helpful SQL expert."
)
```

### 3. Context Export/Import

```python
# Export conversation data
conversation_data = conversation_manager.export_conversation(session_id)

# Import conversation data
new_session_id = conversation_manager.import_conversation(conversation_data)
```

## Error Handling

### Common Scenarios

1. **Context Too Large**
   - System automatically truncates to fit token limits
   - Keeps most recent messages
   - Logs truncation events

2. **Session Not Found**
   - Automatically creates new conversation
   - No errors thrown for missing sessions

3. **LLM Errors**
   - Graceful fallback to error messages
   - Context is preserved for retry attempts

## Performance Considerations

### Memory Management
- Messages are automatically trimmed when limits are exceeded
- Old conversations are cleaned up after configurable time periods
- Token usage is tracked to prevent context overflow

### Token Optimization
- Smart context selection based on relevance
- Configurable token limits per model
- Automatic truncation to stay within limits

## Testing

Use the provided example script to test the system:

```bash
python example_conversation_context.py
```

This will demonstrate:
- Basic conversation flow
- Context-aware follow-ups
- Context clearing and restart
- Different conversation types

## Migration from Existing System

### What Changed
1. **New Services**: Added conversation manager and contextual LLM service
2. **Enhanced Orchestrator**: Now uses contextual LLM for flow determination
3. **New API Endpoints**: Added conversation management endpoints
4. **Automatic Context**: Chat endpoint now maintains context automatically

### What Stayed the Same
1. **API Compatibility**: Existing chat requests work without changes
2. **Flow Logic**: All existing flows work unchanged
3. **Session Management**: Existing session handling preserved
4. **Error Handling**: All existing error handling maintained

## Future Enhancements

### 1. Persistent Storage
- Database integration for conversation persistence
- Redis caching for improved performance
- Conversation search and retrieval

### 2. Advanced Context Management
- Semantic context selection
- Conversation summarization
- Context relevance scoring

### 3. Multi-User Support
- User-specific conversation isolation
- Conversation sharing capabilities
- Team conversation management

### 4. Analytics
- Conversation analytics and insights
- Context usage patterns
- Performance metrics

## Troubleshooting

### Common Issues

1. **Context Not Maintained**
   - Check that session_id is consistent across requests
   - Verify conversation manager is properly initialized
   - Check for context clearing calls

2. **Token Limit Exceeded**
   - Reduce max_context_tokens in configuration
   - Implement more aggressive context truncation
   - Consider conversation summarization

3. **Memory Issues**
   - Reduce max_context_messages
   - Implement conversation cleanup
   - Use persistent storage for long conversations

### Debug Mode

Enable debug logging to see context management:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Conclusion

The conversation context management system provides a robust solution for maintaining conversation coherence across multiple requests. It seamlessly integrates with your existing LLM endpoint while providing the benefits of context-aware conversations.

The system is designed to be:
- **Easy to use**: Minimal changes to existing code
- **Flexible**: Configurable for different use cases
- **Reliable**: Robust error handling and fallbacks
- **Scalable**: Efficient memory and token management

This solution addresses your need for conversation context management without requiring changes to your LLM endpoint, providing a reusable and maintainable solution for context-aware conversations. 