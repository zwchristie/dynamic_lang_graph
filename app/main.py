from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import uuid
import logging

from .services.orchestrator import orchestrator_service
from .services.conversation_manager import conversation_manager, MessageRole
from .services.flow_registry import FlowRegistryService
from .core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    provider: str = "openai"  # "openai", "bedrock", or "custom"
    system_prompt: Optional[str] = None
    clear_context: bool = False
    max_context_messages: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    conversation_id: Optional[str] = None
    provider: str
    selected_flow: Optional[str] = None
    planning: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class FlowRequest(BaseModel):
    flow_name: str
    message: str
    session_id: Optional[str] = None
    provider: str = "openai"
    system_prompt: Optional[str] = None
    clear_context: bool = False

class FlowResponse(BaseModel):
    result: str
    flow_name: str
    session_id: str
    provider: str
    conversation_id: Optional[str] = None
    error: Optional[str] = None

class ConversationRequest(BaseModel):
    session_id: str
    max_messages: Optional[int] = None

class ConversationResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    summary: Dict[str, Any]
    context_size: Dict[str, Any]

class ClearConversationRequest(BaseModel):
    session_id: str

class ClearConversationResponse(BaseModel):
    session_id: str
    success: bool
    message: str

class FlowInfoRequest(BaseModel):
    flow_name: Optional[str] = None

class FlowInfoResponse(BaseModel):
    flows: List[Dict[str, Any]]
    total_flows: int
    categories: Dict[str, int]

# API Endpoints

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint that determines and executes the appropriate flow
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Clear context if requested
        if request.clear_context:
            conversation_manager.clear_conversation(session_id)
        
        # Execute with planning and provider selection
        result = orchestrator_service.execute_with_planning(
            session_id=session_id,
            user_message=request.message,
            provider=request.provider,
            system_prompt=request.system_prompt
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return ChatResponse(
            response=result.get("result", result.get("message", "No response generated")),
            session_id=session_id,
            conversation_id=result.get("conversation_id"),
            provider=request.provider,
            selected_flow=result.get("selected_flow"),
            planning=result.get("planning")
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/flow/{flow_name}", response_model=FlowResponse)
async def execute_specific_flow(flow_name: str, request: FlowRequest):
    """
    Execute a specific flow with conversation context
    """
    try:
        # Use session ID from request or generate new one
        session_id = request.session_id or str(uuid.uuid4())
        
        # Clear context if requested
        if request.clear_context:
            conversation_manager.clear_conversation(session_id)
        
        # Execute the specific flow
        result = orchestrator_service.execute_flow_with_context(
            session_id=session_id,
            flow_name=flow_name,
            user_message=request.message,
            provider=request.provider,
            system_prompt=request.system_prompt
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return FlowResponse(
            result=result.get("result", "No result generated"),
            flow_name=flow_name,
            session_id=session_id,
            provider=request.provider,
            conversation_id=result.get("conversation_id")
        )
        
    except Exception as e:
        logger.error(f"Error executing flow {flow_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/flows", response_model=FlowInfoResponse)
async def get_flows_info(request: FlowInfoRequest = Depends()):
    """
    Get information about available flows
    """
    try:
        flow_registry = FlowRegistryService()
        
        if request.flow_name:
            # Get specific flow info
            flow_info = flow_registry.get_flow_by_name(request.flow_name)
            flows = [flow_info.dict()] if flow_info else []
        else:
            # Get all flows info
            flows = [flow.dict() for flow in flow_registry.get_all_flows()]
        
        stats = flow_registry.get_flow_statistics()
        
        return FlowInfoResponse(
            flows=flows,
            total_flows=stats["total_flows"],
            categories=stats["categories"]
        )
        
    except Exception as e:
        logger.error(f"Error getting flows info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation/context", response_model=ConversationResponse)
async def get_conversation_context(request: ConversationRequest):
    """
    Get conversation context for a session
    """
    try:
        conversation = conversation_manager.get_conversation(request.session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = conversation_manager.get_conversation_messages(
            request.session_id, 
            request.max_messages
        )
        
        summary = conversation_manager.get_conversation_summary(request.session_id)
        
        return ConversationResponse(
            session_id=request.session_id,
            messages=[msg.to_dict() for msg in messages],
            summary=summary,
            context_size={"message_count": len(messages), "estimated_tokens": len(messages) * 100}
        )
        
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation/clear", response_model=ClearConversationResponse)
async def clear_conversation(request: ClearConversationRequest):
    """
    Clear conversation context for a session
    """
    try:
        success = conversation_manager.clear_conversation(request.session_id)
        
        return ClearConversationResponse(
            session_id=request.session_id,
            success=success,
            message="Conversation cleared successfully" if success else "Failed to clear conversation"
        )
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "provider": settings.provider,
        "debug": settings.debug
    }

@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "flow": "/flow/{flow_name}",
            "flows": "/flows",
            "conversation": "/conversation/context",
            "clear_conversation": "/conversation/clear",
            "health": "/health"
        },
        "supported_providers": ["openai", "bedrock", "custom"]
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get SSL context if available
    ssl_context = settings.ssl_context
    
    # Run with SSL if certificates are available
    if ssl_context:
        print(f"Starting server with SSL on {settings.host}:{settings.port}")
        uvicorn.run(
            app, 
            host=settings.host, 
            port=settings.port,
            **ssl_context
        )
    else:
        print(f"Starting server without SSL on {settings.host}:{settings.port}")
        uvicorn.run(
            app, 
            host=settings.host, 
            port=settings.port
        ) 