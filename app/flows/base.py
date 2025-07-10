from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Literal, Union
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..core.config import settings
import json

# Define the state structure for LangGraph 0.5.1
class FlowState(TypedDict):
    messages: List[HumanMessage | AIMessage | SystemMessage]
    session_id: str
    current_step: str
    metadata: Dict[str, Any]
    error: Optional[str]

# Node description structure for dynamic planning
class NodeDescription(TypedDict):
    name: str
    description: str
    inputs: List[str]
    outputs: List[str]
    possible_next_nodes: List[str]
    conditions: Optional[Dict[str, str]]

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
    
    @abstractmethod
    def get_node_descriptions(self) -> List[NodeDescription]:
        """Get descriptions of all nodes in this flow for LLM planning"""
        pass
    
    def get_flow_planning_context(self) -> str:
        """Get formatted context for LLM flow planning"""
        node_descriptions = self.get_node_descriptions()
        
        context = f"Flow: {self.flow_name}\nDescription: {self.get_description()}\n\nAvailable Nodes:\n"
        
        for node in node_descriptions:
            context += f"\n- {node['name']}:\n"
            context += f"  Description: {node['description']}\n"
            context += f"  Inputs: {', '.join(node['inputs'])}\n"
            context += f"  Outputs: {', '.join(node['outputs'])}\n"
            context += f"  Possible next nodes: {', '.join(node['possible_next_nodes'])}\n"
            if node.get('conditions'):
                context += f"  Conditions: {json.dumps(node['conditions'])}\n"
        
        return context
    
    def plan_execution_path(self, user_message: str, current_state: Optional[Dict[str, Any]] = None) -> List[str]:
        """Use LLM to plan the execution path through nodes"""
        llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            api_key=settings.openai_api_key
        )
        
        planning_context = self.get_flow_planning_context()
        
        # Add current state context if provided
        state_context = ""
        if current_state:
            state_context = f"\nCurrent State: {json.dumps(current_state, indent=2)}\n"
        
        planning_prompt = f"""
        You are an execution planner for a workflow system. Based on the user's request and available nodes, 
        determine the optimal execution path.
        
        {planning_context}
        {state_context}
        
        User Request: {user_message}
        
        Analyze the user's request and determine which nodes should be executed and in what order.
        Consider:
        1. What the user is asking for
        2. What inputs are available
        3. What outputs are needed
        4. The logical flow between nodes
        
        Return a JSON array of node names in execution order:
        ["node1", "node2", "node3"]
        
        Only include nodes that are necessary for this specific request.
        """
        
        response = llm.invoke([HumanMessage(content=planning_prompt)])
        
        try:
            # Extract JSON from response
            content = str(response.content)
            # Find JSON array in the response
            import re
            json_match = re.search(r'\[.*?\]', content)
            if json_match:
                planned_path = json.loads(json_match.group())
                return planned_path
            else:
                # Fallback: return all nodes in order
                return [node['name'] for node in self.get_node_descriptions()]
        except Exception as e:
            print(f"Error parsing execution plan: {e}")
            # Fallback: return all nodes in order
            return [node['name'] for node in self.get_node_descriptions()]
    
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
    
    def run_with_planning(self, state: FlowState, user_message: str) -> FlowState:
        """Run the flow with LLM-planned execution path"""
        # Plan the execution path
        planned_path = self.plan_execution_path(user_message, state.get("metadata"))
        
        # Store the planned path in metadata
        state["metadata"]["planned_execution_path"] = planned_path
        state["metadata"]["current_path_index"] = 0
        
        # Run the flow (the graph will handle the execution)
        return self.run(state)
    
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