from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from ..core.config import settings
from ..flows.base import get_all_flows, get_flow_by_name, FlowState
from ..models.schemas import Message, MessageRole
import json

class OrchestratorService:
    """LLM orchestrator that dynamically generates workflows based on available flows"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        self.flows = get_all_flows()
    
    def get_available_flows_context(self) -> str:
        """Get formatted context of all available flows for LLM"""
        flow_descriptions = []
        
        for flow in self.flows:
            flow_descriptions.append(f"**{flow.flow_name}**: {flow.get_description()}")
        
        return "\n\n".join(flow_descriptions)
    
    def determine_appropriate_flow(self, user_message: str, conversation_history: List[Message]) -> str:
        """Use LLM to determine which flow is most appropriate for the user's request"""
        
        # Format conversation history
        history_text = ""
        for msg in conversation_history:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            history_text += f"{role}: {msg.content}\n"
        
        # Get available flows context
        flows_context = self.get_available_flows_context()
        
        system_prompt = f"""
        You are an intelligent workflow orchestrator. Your job is to determine which workflow/flow 
        is most appropriate for handling a user's request.
        
        Available flows:
        {flows_context}
        
        Analyze the user's request and conversation history to determine which flow should handle it.
        Consider the user's intent, the type of request, and any context from the conversation.
        
        Return only the flow name that best matches the request. If no specific flow is needed, 
        return "general_qa" for general questions.
        """
        
        user_prompt = f"""
        Conversation history:
        {history_text}
        
        Current user request: {user_message}
        
        Which flow should handle this request? Return only the flow name.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = self.llm.invoke(messages)
        selected_flow = str(response.content).strip().lower()
        
        # Validate that the selected flow exists
        if selected_flow not in [flow.flow_name for flow in self.flows]:
            selected_flow = "general_qa"  # Default fallback
        
        return selected_flow
    
    def execute_flow(self, flow_name: str, messages: List[Message], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a specific flow with the given messages"""
        
        flow = get_flow_by_name(flow_name)
        if not flow:
            raise ValueError(f"Flow '{flow_name}' not found")
        
        # Convert messages to LangChain format
        lc_messages = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                from langchain.schema import HumanMessage
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                from langchain.schema import AIMessage
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == MessageRole.SYSTEM:
                from langchain.schema import SystemMessage
                lc_messages.append(SystemMessage(content=msg.content))
        
        # Create initial state
        state = FlowState(
            messages=lc_messages,
            session_id=session_id or "default",
            current_step="start"
        )
        
        # Execute the flow
        result_state = flow.run(state)
        
        # Extract the last assistant message as response
        response_content = ""
        for message in reversed(result_state.messages):
            if hasattr(message, 'content'):
                response_content = message.content
                break
        
        return {
            "response": response_content,
            "session_id": result_state.session_id,
            "flow_name": flow_name,
            "metadata": result_state.metadata,
            "error": result_state.error
        }
    
    def process_chat_request(self, messages: List[Message], session_id: Optional[str] = None, specified_flow: Optional[str] = None) -> Dict[str, Any]:
        """Process a chat request by determining the appropriate flow and executing it"""
        
        # Get the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                user_message = msg.content
                break
        
        if not user_message:
            return {
                "response": "I didn't receive any user message to process.",
                "session_id": session_id or "default",
                "flow_name": "error",
                "metadata": {},
                "error": "No user message found"
            }
        
        # Determine which flow to use
        if specified_flow:
            flow_name = specified_flow
        else:
            flow_name = self.determine_appropriate_flow(user_message, messages)
        
        # Execute the flow
        return self.execute_flow(flow_name, messages, session_id)
    
    def get_flow_info(self) -> List[Dict[str, str]]:
        """Get information about all available flows"""
        flow_info = []
        for flow in self.flows:
            flow_info.append({
                "name": flow.flow_name,
                "description": flow.flow_description,
                "detailed_description": flow.get_description()
            })
        return flow_info 