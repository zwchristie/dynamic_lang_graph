from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from functools import wraps
import inspect
from langgraph.graph import StateGraph, END
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel

# Global registry for flows
FLOW_REGISTRY: Dict[str, type['BaseFlow']] = {}

def flow(name: str, description: str):
    """
    Decorator to register a flow with the system.
    
    Args:
        name: Unique name for the flow
        description: Description of what the flow does
    """
    def decorator(cls):
        if not issubclass(cls, BaseFlow):
            raise ValueError(f"Class {cls.__name__} must inherit from BaseFlow")
        
        # Add metadata to the class
        cls.flow_name = name
        cls.flow_description = description
        
        # Register the flow
        FLOW_REGISTRY[name] = cls
        
        return cls
    return decorator

class FlowState(BaseModel):
    """Base state for all flows"""
    messages: List[BaseMessage] = []
    session_id: str = ""
    current_step: str = ""
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None

class BaseFlow(ABC):
    """Base class for all flows"""
    
    flow_name: str
    flow_description: str
    
    def __init__(self):
        self.graph = self._build_graph()
    
    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph for this flow"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a detailed description of what this flow does"""
        pass
    
    def get_available_flows(self) -> List[Dict[str, str]]:
        """Get list of all available flows for LLM context"""
        flows = []
        for name, flow_class in FLOW_REGISTRY.items():
            instance = flow_class()
            flows.append({
                "name": name,
                "description": instance.get_description()
            })
        return flows
    
    def run(self, state: FlowState) -> FlowState:
        """Run the flow with given state"""
        try:
            compiled_graph = self.graph.compile()
            result = compiled_graph.invoke(state.dict())
            return FlowState(**result)
        except Exception as e:
            state.error = str(e)
            return state
    
    def add_message(self, state: FlowState, content: str, role: str = "assistant") -> FlowState:
        """Add a message to the conversation"""
        if role == "user":
            message = HumanMessage(content=str(content))
        else:
            message = AIMessage(content=str(content))
        
        state.messages.append(message)
        return state
    
    def get_last_user_message(self, state: FlowState) -> Optional[str]:
        """Get the last user message"""
        for message in reversed(state.messages):
            if isinstance(message, HumanMessage):
                # Ensure content is a string
                if isinstance(message.content, str):
                    return message.content
                elif isinstance(message.content, list):
                    # If content is a list, join as string
                    return " ".join(str(x) for x in message.content)
                else:
                    return str(message.content)
        return None
    
    def get_conversation_history(self, state: FlowState) -> str:
        """Get formatted conversation history"""
        history = []
        for message in state.messages:
            if isinstance(message, HumanMessage):
                history.append(f"User: {message.content}")
            elif isinstance(message, AIMessage):
                history.append(f"Assistant: {message.content}")
        return "\n".join(history)

def get_flow_by_name(name: str) -> Optional[BaseFlow]:
    """Get a flow instance by name"""
    if name in FLOW_REGISTRY:
        return FLOW_REGISTRY[name]()
    return None

def get_all_flows() -> List[BaseFlow]:
    """Get all registered flow instances"""
    return [flow_class() for flow_class in FLOW_REGISTRY.values()] 