from typing import Dict, Any, List, Optional, Tuple
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..core.config import settings
from .conversation_manager import conversation_manager, MessageRole
import logging

logger = logging.getLogger(__name__)

class ContextualLLMService:
    """LLM service that maintains conversation context"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        self.max_context_tokens = 4000  # Adjust based on your model's context window
    
    def invoke_with_context(
        self, 
        session_id: str, 
        user_message: str, 
        system_prompt: Optional[str] = None,
        max_context_messages: Optional[int] = None,
        clear_context: bool = False
    ) -> Tuple[str, Optional[str]]:
        """
        Invoke LLM with conversation context
        
        Args:
            session_id: Session identifier
            user_message: Current user message
            system_prompt: Optional system prompt
            max_context_messages: Maximum number of context messages to include
            clear_context: Whether to clear existing context
            
        Returns:
            Tuple of (response_content, conversation_id)
        """
        try:
            # Add user message to conversation
            conversation_manager.add_message(
                session_id=session_id,
                role=MessageRole.USER,
                content=user_message
            )
            
            # Get conversation context
            if clear_context:
                conversation_manager.clear_conversation(session_id)
                # Re-add the current user message
                conversation_manager.add_message(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=user_message
                )
            
            # Get context messages for LLM
            context_messages = conversation_manager.get_context_for_llm(
                session_id=session_id,
                max_tokens=self.max_context_tokens
            )
            
            # Limit context messages if specified
            if max_context_messages and len(context_messages) > max_context_messages:
                context_messages = context_messages[-max_context_messages:]
            
            # Prepare messages for LLM
            llm_messages = []
            
            # Add system prompt if provided
            if system_prompt:
                llm_messages.append(SystemMessage(content=system_prompt))
            
            # Add conversation context
            for msg in context_messages:
                if msg["role"] == "user":
                    llm_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    llm_messages.append(AIMessage(content=msg["content"]))
                elif msg["role"] == "system":
                    llm_messages.append(SystemMessage(content=msg["content"]))
            
            # Invoke LLM
            response = self.llm.invoke(llm_messages)
            response_content = str(response.content)
            
            # Add assistant response to conversation
            conversation_manager.add_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=response_content
            )
            
            # Get conversation ID
            conversation = conversation_manager.get_conversation(session_id)
            conversation_id = conversation.id if conversation else None
            
            return response_content, conversation_id
            
        except Exception as e:
            logger.error(f"Error in contextual LLM invocation: {e}")
            return f"Error: {str(e)}", None
    
    def invoke_chat_with_context(
        self, 
        session_id: str, 
        user_message: str, 
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_context_messages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Invoke LLM with context and return structured response
        
        Args:
            session_id: Session identifier
            user_message: Current user message
            model_name: Optional model name override
            system_prompt: Optional system prompt
            max_context_messages: Maximum context messages to include
            
        Returns:
            Dictionary with response data
        """
        try:
            response_content, conversation_id = self.invoke_with_context(
                session_id=session_id,
                user_message=user_message,
                system_prompt=system_prompt,
                max_context_messages=max_context_messages
            )
            
            return {
                "Message": response_content,
                "ConversationId": conversation_id,
                "SessionId": session_id,
                "Model": model_name or settings.openai_model,
                "ContextMessages": len(conversation_manager.get_conversation_messages(session_id))
            }
            
        except Exception as e:
            logger.error(f"Error in chat invocation: {e}")
            return {
                "Message": f"Error: {str(e)}",
                "ConversationId": None,
                "SessionId": session_id,
                "Model": model_name or settings.openai_model,
                "Error": str(e)
            }
    
    def get_conversation_context(self, session_id: str, max_messages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation context for a session"""
        messages = conversation_manager.get_conversation_messages(session_id, max_messages)
        return [msg.to_dict() for msg in messages]
    
    def clear_conversation_context(self, session_id: str) -> bool:
        """Clear conversation context for a session"""
        return conversation_manager.clear_conversation(session_id)
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get conversation summary"""
        return conversation_manager.get_conversation_summary(session_id)
    
    def add_system_message(self, session_id: str, system_message: str) -> str:
        """Add a system message to the conversation"""
        return conversation_manager.add_message(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=system_message
        )
    
    def get_context_size(self, session_id: str) -> Dict[str, Any]:
        """Get context size information"""
        conversation = conversation_manager.get_conversation(session_id)
        if not conversation:
            return {"message_count": 0, "estimated_tokens": 0}
        
        total_chars = sum(len(msg.content) for msg in conversation.messages)
        estimated_tokens = total_chars // 4  # Rough estimation
        
        return {
            "message_count": len(conversation.messages),
            "estimated_tokens": estimated_tokens,
            "max_tokens": self.max_context_tokens,
            "context_usage_percent": (estimated_tokens / self.max_context_tokens) * 100
        }

# Global contextual LLM service instance
contextual_llm_service = ContextualLLMService() 