from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..core.config import settings

# Define the state structure for LangGraph 0.5.1
class FlowState(TypedDict):
    messages: List[HumanMessage | AIMessage | SystemMessage]
    session_id: str
    current_step: str
    metadata: Dict[str, Any]
    error: Optional[str]

# Flow registry for automatic discovery
FLOW_REGISTRY: Dict[str, type] = {}

def flow(name: str, description: str):
    """Decorator to register a flow with the system"""
    def decorator(cls):
        cls.flow_name = name
        cls.flow_description = description
        FLOW_REGISTRY[name] = cls
        return cls
    return decorator

class BaseFlow(ABC):
    """Base class for all flows using LangGraph 0.5.1"""
    
    flow_name: str
    flow_description: str
    
    def __init__(self):
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()
    
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
        """Run the flow with given state using LangGraph 0.5.1"""
        try:
            result = self.compiled_graph.invoke(state)
            return result  # type: ignore
        except Exception as e:
            state["error"] = str(e)
            return state
    
    def add_message(self, state: FlowState, content: str, role: str = "assistant") -> FlowState:
        """Add a message to the conversation"""
        if role == "user":
            message = HumanMessage(content=str(content))
        else:
            message = AIMessage(content=str(content))
        
        state["messages"].append(message)
        return state
    
    def get_last_user_message(self, state: FlowState) -> Optional[str]:
        """Get the last user message from the conversation"""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                if isinstance(msg.content, str):
                    return msg.content
                else:
                    return str(msg.content)
        return None

def get_flow_by_name(name: str) -> Optional[BaseFlow]:
    """Get a flow instance by name"""
    if name in FLOW_REGISTRY:
        return FLOW_REGISTRY[name]()
    return None

def get_all_flows() -> List[BaseFlow]:
    """Get all registered flow instances"""
    return [flow_class() for flow_class in FLOW_REGISTRY.values()] 