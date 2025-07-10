from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class ConversationMessage:
    """Represents a message in a conversation"""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary"""
        return cls(
            id=data["id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )

@dataclass
class Conversation:
    """Represents a conversation with context"""
    id: str
    session_id: str
    messages: List[ConversationMessage]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    max_messages: int = 50  # Limit to prevent memory issues
    
    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a message to the conversation"""
        message_id = str(uuid.uuid4())
        message = ConversationMessage(
            id=message_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # Trim old messages if we exceed the limit
        if len(self.messages) > self.max_messages:
            # Keep the most recent messages
            self.messages = self.messages[-self.max_messages:]
        
        return message_id
    
    def get_recent_messages(self, count: int = 10) -> List[ConversationMessage]:
        """Get the most recent messages"""
        return self.messages[-count:] if self.messages else []
    
    def get_messages_for_context(self, max_tokens: Optional[int] = None) -> List[ConversationMessage]:
        """Get messages optimized for LLM context"""
        if not max_tokens:
            return self.messages
        
        # Simple token estimation (roughly 4 chars per token)
        estimated_tokens = 0
        context_messages = []
        
        for message in reversed(self.messages):
            message_tokens = len(message.content) // 4
            if estimated_tokens + message_tokens > max_tokens:
                break
            context_messages.insert(0, message)
            estimated_tokens += message_tokens
        
        return context_messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata or {},
            "max_messages": self.max_messages
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create from dictionary"""
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            messages=[ConversationMessage.from_dict(msg) for msg in data["messages"]],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
            max_messages=data.get("max_messages", 50)
        )

class ConversationManager:
    """Manages conversation context and history"""
    
    def __init__(self, storage_backend: str = "memory"):
        self.storage_backend = storage_backend
        self.conversations: Dict[str, Conversation] = {}
        self.session_to_conversation: Dict[str, str] = {}  # session_id -> conversation_id
    
    def create_conversation(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            session_id=session_id,
            messages=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata
        )
        
        self.conversations[conversation_id] = conversation
        self.session_to_conversation[session_id] = conversation_id
        
        return conversation_id
    
    def get_or_create_conversation(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Get existing conversation or create new one"""
        if session_id in self.session_to_conversation:
            return self.session_to_conversation[session_id]
        
        return self.create_conversation(session_id, metadata)
    
    def add_message(self, session_id: str, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a message to the conversation"""
        conversation_id = self.get_or_create_conversation(session_id)
        conversation = self.conversations[conversation_id]
        
        return conversation.add_message(role, content, metadata)
    
    def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """Get conversation for a session"""
        if session_id not in self.session_to_conversation:
            return None
        
        conversation_id = self.session_to_conversation[session_id]
        return self.conversations.get(conversation_id)
    
    def get_conversation_messages(self, session_id: str, max_messages: Optional[int] = None) -> List[ConversationMessage]:
        """Get messages for a conversation"""
        conversation = self.get_conversation(session_id)
        if not conversation:
            return []
        
        if max_messages:
            return conversation.get_recent_messages(max_messages)
        return conversation.messages
    
    def get_context_for_llm(self, session_id: str, max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation context formatted for LLM"""
        conversation = self.get_conversation(session_id)
        if not conversation:
            return []
        
        context_messages = conversation.get_messages_for_context(max_tokens)
        
        # Convert to LLM format
        llm_messages = []
        for message in context_messages:
            llm_messages.append({
                "role": message.role.value,
                "content": message.content
            })
        
        return llm_messages
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation"""
        conversation = self.get_conversation(session_id)
        if not conversation:
            return {}
        
        return {
            "conversation_id": conversation.id,
            "session_id": conversation.session_id,
            "message_count": len(conversation.messages),
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "metadata": conversation.metadata
        }
    
    def clear_conversation(self, session_id: str) -> bool:
        """Clear a conversation"""
        if session_id not in self.session_to_conversation:
            return False
        
        conversation_id = self.session_to_conversation[session_id]
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
        
        del self.session_to_conversation[session_id]
        return True
    
    def cleanup_old_conversations(self, max_age_hours: int = 24) -> int:
        """Clean up old conversations"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        conversations_to_remove = []
        
        for conversation_id, conversation in self.conversations.items():
            if conversation.updated_at < cutoff_time:
                conversations_to_remove.append(conversation_id)
        
        for conversation_id in conversations_to_remove:
            conversation = self.conversations[conversation_id]
            if conversation.session_id in self.session_to_conversation:
                del self.session_to_conversation[conversation.session_id]
            del self.conversations[conversation_id]
        
        return len(conversations_to_remove)
    
    def export_conversation(self, session_id: str) -> Dict[str, Any]:
        """Export conversation data"""
        conversation = self.get_conversation(session_id)
        if not conversation:
            return {}
        
        return conversation.to_dict()
    
    def import_conversation(self, data: Dict[str, Any]) -> str:
        """Import conversation data"""
        conversation = Conversation.from_dict(data)
        self.conversations[conversation.id] = conversation
        self.session_to_conversation[conversation.session_id] = conversation.id
        return conversation.id

# Global conversation manager instance
conversation_manager = ConversationManager() 