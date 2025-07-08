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

class ChatResponse(BaseModel):
    response: str
    session_id: str
    flow_name: str
    metadata: Optional[Dict[str, Any]] = None

class ValidationRequest(BaseModel):
    session_id: str
    validation_type: str  # "table_selection", "query_validation"
    data: Dict[str, Any]
    user_response: bool

class ValidationResponse(BaseModel):
    session_id: str
    approved: bool
    message: str

class FlowInfo(BaseModel):
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None

class FlowRegistration(BaseModel):
    name: str
    description: str
    flow_class: str

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