from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    role: MessageRole
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[str] = None
    flow_name: Optional[str] = None
    use_planning: Optional[bool] = True

class ChatResponse(BaseModel):
    response: str
    session_id: str
    flow_name: str
    metadata: Optional[Dict[str, Any]] = None
    planned_path: Optional[List[str]] = None

class ValidationRequest(BaseModel):
    session_id: str
    step_name: str
    approved: bool
    feedback: Optional[str] = None

class ValidationResponse(BaseModel):
    session_id: str
    step_name: str
    approved: bool
    message: str

class FlowInfo(BaseModel):
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None
    node_count: Optional[int] = None

class FlowRegistration(BaseModel):
    name: str
    description: str
    flow_class: str

class NodeDescription(BaseModel):
    name: str
    description: str
    inputs: List[str]
    outputs: List[str]
    possible_next_nodes: List[str]
    conditions: Optional[Dict[str, str]] = None

class FlowPlanningInfo(BaseModel):
    name: str
    description: str
    nodes: List[NodeDescription]
    planning_context: str

class ExecutionPlanRequest(BaseModel):
    flow_name: str
    user_message: str
    current_state: Optional[Dict[str, Any]] = None

class ExecutionPlanResponse(BaseModel):
    flow_name: str
    user_message: str
    planned_path: List[str]
    node_count: int

class SQLQueryRequest(BaseModel):
    query: str
    operation_type: str = Field(..., description="new, edit, fix, fix_previous")
    existing_sql: Optional[str] = None
    context: Optional[str] = None

class TableSelection(BaseModel):
    tables: List[str]
    reasoning: str

class ColumnSelection(BaseModel):
    table: str
    columns: List[str]
    reasoning: str

class SQLGenerationResult(BaseModel):
    sql: str
    explanation: str
    tables_used: List[str]
    columns_used: List[str] 