import logging
from typing import Dict, Any, List, Optional, Union
from langchain_core.language_models import BaseLLM
from langchain_community.llms import Bedrock
from langchain_openai import ChatOpenAI
from .flow_registry import FlowRegistryService
from .conversation_manager import conversation_manager, MessageRole
from .contextual_llm_service import contextual_llm_service
from .custom_llm_connector import contextual_custom_llm_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class OrchestratorService:
    """Orchestrator service that manages flow execution and LLM provider selection"""
    
    def __init__(self):
        self.flow_registry = FlowRegistryService()
        self.contextual_llm_service = contextual_llm_service
        self.contextual_custom_llm_service = contextual_custom_llm_service
        self._initialize_llm_providers()
    
    def _initialize_llm_providers(self):
        """Initialize different LLM providers"""
        self.llm_providers = {
            "openai": self._create_openai_llm(),
            "bedrock": self._create_bedrock_llm(),
            "custom": self.contextual_custom_llm_service
        }
    
    def _create_openai_llm(self) -> Optional[Union[BaseLLM, ChatOpenAI]]:
        """Create OpenAI LLM instance"""
        try:
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                temperature=0.1
            )
        except Exception as e:
            logger.error(f"Failed to create OpenAI LLM: {e}")
            return None
    
    def _create_bedrock_llm(self) -> Optional[Union[BaseLLM, Bedrock]]:
        """Create Bedrock LLM instance"""
        try:
            return Bedrock(
                region_name=settings.bedrock_region,
                aws_access_key_id=settings.bedrock_access_key.get_secret_value() if settings.bedrock_access_key else None,
                aws_secret_access_key=settings.bedrock_secret_key.get_secret_value() if settings.bedrock_secret_key else None,
                model_id=settings.bedrock_llm_model_id or "anthropic.claude-3-sonnet-20240229-v1:0",
                model_kwargs={"temperature": 0.1}
            )
        except Exception as e:
            logger.error(f"Failed to create Bedrock LLM: {e}")
            return None
    
    def get_llm_provider(self, provider: str = "openai"):
        """Get LLM provider based on provider name"""
        return self.llm_providers.get(provider)
    
    def determine_flow_with_context(
        self, 
        session_id: str, 
        user_message: str, 
        available_flows: Optional[List[str]] = None,
        provider: str = "openai",
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determine the best flow to execute using LLM with conversation context
        
        Args:
            session_id: Session identifier
            user_message: User's message
            available_flows: List of available flow names (if None, uses all registered flows)
            provider: LLM provider to use ("openai", "bedrock", or "custom")
            system_prompt: Optional system prompt for flow determination
            
        Returns:
            Dictionary with flow determination results
        """
        try:
            # Get available flows
            if available_flows is None:
                available_flows = self.flow_registry.list_flow_names()
            
            # Create flow selection prompt
            flow_descriptions = []
            for flow_name in available_flows:
                flow_info = self.flow_registry.get_flow_by_name(flow_name)
                if flow_info:
                    description = flow_info.description
                    flow_descriptions.append(f"- {flow_name}: {description}")
            
            flows_text = "\n".join(flow_descriptions)
            
            # Create system prompt for flow determination
            flow_system_prompt = system_prompt or f"""
You are an AI assistant that determines the best workflow to execute based on user requests.

Available workflows:
{flows_text}

Please analyze the user's request and determine which workflow would be most appropriate.
Respond with the exact flow name from the list above, or "none" if no flow matches.

User request: {user_message}
"""
            
            # Use appropriate LLM provider
            if provider == "custom":
                # Use custom LLM service
                response_content, conversation_id = self.contextual_custom_llm_service.invoke_with_context(
                    session_id=session_id,
                    user_message=user_message,
                    system_prompt=flow_system_prompt,
                    deployment_id="text_to_sql"  # Default deployment for flow determination
                )
                
                # Extract flow name from response
                flow_name = self._extract_flow_name_from_response(response_content, available_flows)
                
                return {
                    "selected_flow": flow_name,
                    "reasoning": response_content,
                    "conversation_id": conversation_id,
                    "provider": "custom",
                    "available_flows": available_flows
                }
            else:
                # Use standard LLM providers (OpenAI/Bedrock)
                llm = self.get_llm_provider(provider)
                if not llm:
                    return {
                        "error": f"LLM provider '{provider}' not available",
                        "available_flows": available_flows
                    }
                
                # Use contextual LLM service
                response_content, conversation_id = self.contextual_llm_service.invoke_with_context(
                    session_id=session_id,
                    user_message=user_message,
                    system_prompt=flow_system_prompt
                )
                
                # Extract flow name from response
                flow_name = self._extract_flow_name_from_response(response_content, available_flows)
                
                return {
                    "selected_flow": flow_name,
                    "reasoning": response_content,
                    "conversation_id": conversation_id,
                    "provider": provider,
                    "available_flows": available_flows
                }
                
        except Exception as e:
            logger.error(f"Error in flow determination: {e}")
            return {
                "error": str(e),
                "available_flows": available_flows or []
            }
    
    def _extract_flow_name_from_response(self, response: str, available_flows: List[str]) -> Optional[str]:
        """Extract flow name from LLM response"""
        try:
            # Clean the response
            response_lower = response.lower().strip()
            
            # Check for exact matches
            for flow_name in available_flows:
                if flow_name.lower() in response_lower:
                    return flow_name
            
            # Check for "none" or "no flow"
            if "none" in response_lower or "no flow" in response_lower:
                return None
            
            # If no exact match, return the first available flow as fallback
            return available_flows[0] if available_flows else None
            
        except Exception as e:
            logger.error(f"Error extracting flow name: {e}")
            return available_flows[0] if available_flows else None
    
    def execute_flow_with_context(
        self, 
        session_id: str, 
        flow_name: str, 
        user_message: str,
        provider: str = "openai",
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a specific flow with conversation context
        
        Args:
            session_id: Session identifier
            flow_name: Name of the flow to execute
            user_message: User's message
            provider: LLM provider to use ("openai", "bedrock", or "custom")
            system_prompt: Optional system prompt
            **kwargs: Additional arguments for flow execution
            
        Returns:
            Dictionary with flow execution results
        """
        try:
            # Get the flow
            flow_info = self.flow_registry.get_flow_by_name(flow_name)
            if not flow_info:
                return {
                    "error": f"Flow '{flow_name}' not found",
                    "available_flows": self.flow_registry.list_flow_names()
                }
            
            # Get LLM provider
            if provider == "custom":
                llm_provider = self.contextual_custom_llm_service
            else:
                llm_provider = self.get_llm_provider(provider)
                if not llm_provider:
                    return {
                        "error": f"LLM provider '{provider}' not available"
                    }
            
            # Execute flow with context
            if provider == "custom":
                # Use custom LLM service for flow execution
                response_content, conversation_id = self.contextual_custom_llm_service.invoke_with_context(
                    session_id=session_id,
                    user_message=user_message,
                    system_prompt=system_prompt,
                    deployment_id=flow_name,  # Use flow name as deployment ID
                    **kwargs
                )
                
                return {
                    "flow_name": flow_name,
                    "result": response_content,
                    "conversation_id": conversation_id,
                    "provider": "custom",
                    "session_id": session_id
                }
            else:
                # Use standard LLM providers
                # For now, we'll use the contextual LLM service directly
                # since the flow execution method needs to be updated
                response_content, conversation_id = self.contextual_llm_service.invoke_with_context(
                    session_id=session_id,
                    user_message=user_message,
                    system_prompt=system_prompt
                )
                
                result = response_content
                
                return {
                    "flow_name": flow_name,
                    "result": result,
                    "provider": provider,
                    "session_id": session_id
                }
                
        except Exception as e:
            logger.error(f"Error executing flow '{flow_name}': {e}")
            return {
                "error": str(e),
                "flow_name": flow_name,
                "provider": provider
            }
    
    def execute_with_planning(
        self, 
        session_id: str, 
        user_message: str,
        provider: str = "openai",
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute workflow with LLM-driven planning and conversation context
        
        Args:
            session_id: Session identifier
            user_message: User's message
            provider: LLM provider to use ("openai", "bedrock", or "custom")
            system_prompt: Optional system prompt
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Step 1: Determine the best flow
            flow_determination = self.determine_flow_with_context(
                session_id=session_id,
                user_message=user_message,
                provider=provider,
                system_prompt=system_prompt
            )
            
            if "error" in flow_determination:
                return flow_determination
            
            selected_flow = flow_determination.get("selected_flow")
            if not selected_flow:
                return {
                    "message": "No appropriate flow found for your request",
                    "reasoning": flow_determination.get("reasoning", ""),
                    "provider": provider
                }
            
            # Step 2: Execute the selected flow
            execution_result = self.execute_flow_with_context(
                session_id=session_id,
                flow_name=selected_flow,
                user_message=user_message,
                provider=provider,
                system_prompt=system_prompt,
                **kwargs
            )
            
            # Combine results
            return {
                **execution_result,
                "planning": flow_determination,
                "selected_flow": selected_flow
            }
            
        except Exception as e:
            logger.error(f"Error in planning execution: {e}")
            return {
                "error": str(e),
                "provider": provider
            }

# Global orchestrator service instance
orchestrator_service = OrchestratorService() 