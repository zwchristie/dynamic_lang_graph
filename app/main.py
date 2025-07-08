from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from .core.config import settings
from .models.schemas import (
    ChatRequest, ChatResponse, ValidationRequest, ValidationResponse,
    FlowInfo, FlowRegistration
)
from .services.orchestrator import OrchestratorService
from .services.flow_registry import FlowRegistryService

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Dynamic agentic workflow system with LangGraph and FastAPI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
orchestrator = OrchestratorService()
flow_registry = FlowRegistryService()

# Session storage (in production, use Redis or database)
session_storage: Dict[str, Dict[str, Any]] = {}

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "Agentic Workflow System API",
        "version": "1.0.0",
        "available_endpoints": [
            "/api/chat",
            "/api/flows",
            "/api/validate",
            "/docs"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "flows_count": flow_registry.get_flow_count()
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for agentic workflows.
    
    The orchestrator will automatically determine the appropriate flow
    based on the user's request and conversation history.
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Process the chat request
        result = orchestrator.process_chat_request(
            messages=request.messages,
            session_id=session_id,
            specified_flow=request.flow_name
        )
        
        # Store session data
        session_storage[session_id] = {
            "last_flow": result["flow_name"],
            "metadata": result.get("metadata", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            flow_name=result["flow_name"],
            metadata=result.get("metadata", {})
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.get("/api/flows", response_model=List[FlowInfo])
async def get_flows():
    """Get all available flows"""
    try:
        return flow_registry.get_all_flows()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving flows: {str(e)}")

@app.get("/api/flows/{flow_name}", response_model=FlowInfo)
async def get_flow(flow_name: str):
    """Get information about a specific flow"""
    try:
        flow_info = flow_registry.get_flow_by_name(flow_name)
        if not flow_info:
            raise HTTPException(status_code=404, detail=f"Flow '{flow_name}' not found")
        return flow_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving flow: {str(e)}")

@app.post("/api/flows/register")
async def register_flow(registration: FlowRegistration):
    """Register a new flow dynamically"""
    try:
        if not flow_registry.validate_flow_name(registration.name):
            raise HTTPException(
                status_code=400, 
                detail="Invalid flow name. Must be lowercase alphanumeric with underscores."
            )
        
        success = flow_registry.register_flow(registration)
        if not success:
            raise HTTPException(
                status_code=409, 
                detail=f"Flow '{registration.name}' already exists"
            )
        
        return {
            "message": f"Flow '{registration.name}' registered successfully",
            "flow_name": registration.name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering flow: {str(e)}")

@app.get("/api/flows/statistics")
async def get_flow_statistics():
    """Get statistics about registered flows"""
    try:
        return flow_registry.get_flow_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving flow statistics: {str(e)}")

@app.post("/api/validate", response_model=ValidationResponse)
async def validate_step(request: ValidationRequest):
    """
    Human-in-the-loop validation endpoint.
    
    This endpoint handles validation requests from flows that require
    human approval (e.g., table selection, SQL validation).
    """
    try:
        session_id = request.session_id
        
        # Store validation result in session
        if session_id not in session_storage:
            session_storage[session_id] = {}
        
        session_storage[session_id]["validation_result"] = {
            "type": request.validation_type,
            "approved": request.user_response,
            "data": request.data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update flow state based on validation
        if request.validation_type == "table_selection":
            session_storage[session_id]["table_validation_approved"] = request.user_response
        elif request.validation_type == "query_validation":
            session_storage[session_id]["sql_validation_approved"] = request.user_response
        
        return ValidationResponse(
            session_id=session_id,
            approved=request.user_response,
            message=f"Validation {'approved' if request.user_response else 'rejected'}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing validation: {str(e)}")

@app.get("/api/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    try:
        if session_id not in session_storage:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "data": session_storage[session_id]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving session: {str(e)}")

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    try:
        if session_id in session_storage:
            del session_storage[session_id]
            return {"message": f"Session '{session_id}' deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

@app.get("/api/orchestrator/flows")
async def get_orchestrator_flows():
    """Get the orchestrator's view of available flows"""
    try:
        return orchestrator.get_flow_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving orchestrator flows: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 