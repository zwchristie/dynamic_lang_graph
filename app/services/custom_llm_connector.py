import requests
import time
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from ..core.config import settings
from .conversation_manager import conversation_manager, MessageRole
import logging

logger = logging.getLogger(__name__)

def remove_special_characters(text, keep_chars="?"):
    pattern = f"[^a-zA-Z0-9{re.escape(keep_chars)} ]"
    cleaned_text = re.sub(pattern, '', text)
    return cleaned_text

def parse_user_prompt(text):
    start_marker = "### User Query:\n"
    start_pos = text.find(start_marker)  # sets index at start

    # make sure it exists
    if start_pos == -1:
        print(f'Invalid start position for user query -- stopping')
        return

    # move index to end
    start_pos += len(start_marker)
    end_pos = text.find("### Example response", start_pos)

    if end_pos == -1:
        print(f'Invalid end pos for user query -- stopping')
        return

    print(f'start pos : {start_pos}')
    print(f'end pos : {end_pos}')

    user_query = remove_special_characters(text[start_pos:end_pos].strip())
    return user_query

def parse_json_from_response(response):
    # Remove the backticks and parse the JSON content
    try:
        # Extract the JSON part from the message
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        json_content = response[json_start:json_end]

        # Parse the JSON content
        parsed_content = json.loads(json_content)

        return parsed_content
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing json from response: {e}")
        return {}

def get_deployment_by_name(deployments, deployment_name):
    for deployment in deployments:
        if deployment.get('DeploymentName') == deployment_name:
            print(f"Found deployment: {deployment}")
            return deployment
    print(f"No deployment found with the name: {deployment_name}")
    return None

class LLMApi:
    def __init__(self, tenant_id, token, token_expiry=None):
        self.base_url = settings.custom_base_url
        self.tenant_id = settings.custom_tenant_id
        self.token = token
        self.token_expiry = None
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.deployments = self.fetch_deployments()

    def fetch_deployments(self):
        """Fetch and store deployment IDs for quick access."""
        self.refresh_token_if_needed()  # Refresh token if needed
        get_deployments_url = f"{self.base_url}/chat/api/v2/deployments?tenant_id={self.tenant_id}"
        res = requests.get(get_deployments_url, headers=self.headers)

        if res.status_code == 200:
            deployments = res.json()
            deployment_dict = {
                "text_to_sql": get_deployment_by_name(deployments, deployment_name="text_to_sql"),
                "text_to_sql_o3mini": get_deployment_by_name(deployments, deployment_name="text_to_sql_o3mini")
            }
            return deployment_dict
        else:
            new_token = self.generate_new_token()
            if new_token:
                self.headers["Authorization"] = f"Bearer {new_token}"
                return self.fetch_deployments()
            return {}

    def get_deployment_id(self, deployment_name):
        deployment = self.deployments.get(deployment_name)
        return deployment.get('DeploymentId') if deployment else None

    def get_knowledgebase_id(self, deployment_name):
        deployment = self.deployments.get(deployment_name)
        if deployment and deployment.get('KnowledgeSources') and len(deployment.get('KnowledgeSources', [])) > 0:
            return deployment.get('KnowledgeSources')[0]
        return None

    def generate_new_token(self):
        """Function to generate a new token."""
        print(f'GENERATING NEW TOKEN ... ')
        token_url = "https://idag2.jpmorganchase.com/adfs/oauth2/token"
        data = {
            
        }

        res = requests.post(token_url, data=data)
        if res.status_code == 200:
            token_data = res.json()
            self.token_expiry = time.time() + token_data.get("expires_in", 3600)  # Set expiry time
            return token_data.get("access_token")
        else:
            print(f"Failed to get token: {res.status_code} - {res.text}")
            return None

    def refresh_token_if_needed(self):
        """Refresh the token if it is about to expire."""
        if self.token_expiry and time.time() > self.token_expiry - 300:  # Refresh 5 minutes before expiry
            new_token = self.generate_new_token()
            if new_token:
                self.token = new_token
                self.headers["Authorization"] = f"Bearer {self.token}"
                # print("Token refreshed successfully.")

    def invoke(self, message, deployment_id="text_to_sql", conversation_id=None):
        self.refresh_token_if_needed()  # Refresh token if needed
        deployment_id = self.get_deployment_id(deployment_id)
        if deployment_id is None:
            # print("Deployment ID is not set.")
            return None, "Deployment ID is not set."

        url = f"{self.base_url}/chat/api/v2/invoke?deployment_id={deployment_id}"
        payload = {"Message": message}
        if conversation_id is not None:
            payload["ConversationId"] = conversation_id

        try:
            res = requests.post(url, json=payload, headers=self.headers)

            # Check if the response is empty
            if not res.text:
                return None, "Empty response from LLM"

            # Attempt to parse the response as JSON
            try:
                response_json = res.json()
                # print(f'response from LLM : {res}, {response_json}')
            except json.JSONDecodeError:
                # print(f"Non-JSON response from LLM: {res.text}")
                return None, "Non-JSON response from LLM"

            if res.status_code == 200:
                # print(f'response 200: {response_json}')
                return response_json, None
            else:
                # print(f"Failed to invoke chat: {res.status_code} - {res.text}")
                return None, f"Failed to invoke chat: {res.status_code} - {res.text}"

        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return None, f"Request failed: {e}"

    def get_current_chat(self, conversation_id):
        self.refresh_token_if_needed()  # Refresh token if needed
        get_chat_history_url = f"https://cs.prod.aws.jpmchase.net/chat/api/v2/conversations/{conversation_id}/tenants/{self.tenant_id}"
        res = requests.get(get_chat_history_url, headers=self.headers)
        if res.status_code != 200:
            return None, "Failed to invoke chat history"

        res_json = res.json()
        filtered_conversation_history = []

        # Filter and process the response
        for question in res_json.get('Questions', []):
            answer = question.get('Answer', '')
            if "Approach" in answer:
                question_value = question['Question']
                user_query = parse_user_prompt(question_value)
                print(f'user query to be inserted : {user_query}')
                # Construct the conversation history entry
                question = {
                    'Answer': answer,
                    'Question': question_value,
                    'CreatedTimestamp': question.get('CreatedTimestamp', '')
                }
                filtered_conversation_history.append(question)
        history_json = {'Questions': filtered_conversation_history}
        return history_json, None

    def invoke_qa(self, message, system_prompt, deployment_id, conversation_id=None):
        self.refresh_token_if_needed()  # Refresh token if needed
        knowledgebase_id = self.get_knowledgebase_id(deployment_id)
        if knowledgebase_id is None:
            print("Knowledgebase ID is not set.")
            return None, "Knowledgebase ID is not set."

        url = f"{self.base_url}/qanda/cp/inference/qa?tenant_id={self.tenant_id}&knowledgebase_id={knowledgebase_id}"
        payload = {
            "Prompt": [{
                "UserMsg": message,
                "AssistantMsg": system_prompt
            }]
        }

        if conversation_id is not None:
            payload["ConversationId"] = conversation_id

        try:
            res = requests.post(url, json=payload, headers=self.headers)

            # Check if the response is empty
            if not res.text:
                print("Empty response from LLM")
                return None, "Empty response from LLM"

            # Attempt to parse the response as JSON
            try:
                response_json = res.json()
                print(f'response from LLM : {response_json}')
            except json.JSONDecodeError:
                print(f"Non-JSON response from LLM: {res.text}")
                return None, "Non-JSON response from LLM"

            if res.status_code == 200:
                return response_json, None
            else:
                print(f"Failed to invoke chat: {res.status_code} - {res.text}")
                return None, f"Failed to invoke chat: {res.status_code} - {res.text}"
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return None, f"Request failed: {e}"

class ContextualCustomLLMService:
    """Contextual LLM service that works with your custom LLM API"""
    
    def __init__(self):
        self.llm_api = None
        self.max_context_tokens = 4000
        self._initialize_llm_api()
    
    def _initialize_llm_api(self):
        """Initialize the LLM API with your custom connector"""
        try:
            # Initialize with your custom settings
            tenant_id = settings.custom_tenant_id
            token = self._generate_initial_token()
            self.llm_api = LLMApi(tenant_id, token)
        except Exception as e:
            logger.error(f"Failed to initialize custom LLM API: {e}")
            self.llm_api = None
    
    def _generate_initial_token(self):
        """Generate initial token for the LLM API"""
        # This would use your token generation logic
        # For now, we'll use a placeholder
        return "initial_token"
    
    def invoke_with_context(
        self, 
        session_id: str, 
        user_message: str, 
        system_prompt: Optional[str] = None,
        max_context_messages: Optional[int] = None,
        clear_context: bool = False,
        deployment_id: str = "text_to_sql"
    ) -> Tuple[str, Optional[str]]:
        """
        Invoke custom LLM with conversation context
        
        Args:
            session_id: Session identifier
            user_message: Current user message
            system_prompt: Optional system prompt
            max_context_messages: Maximum number of context messages to include
            clear_context: Whether to clear existing context
            deployment_id: Custom deployment ID to use
            
        Returns:
            Tuple of (response_content, conversation_id)
        """
        try:
            if not self.llm_api:
                return "Error: LLM API not initialized", None
            
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
            
            # Prepare the message with context
            if system_prompt:
                full_message = f"{system_prompt}\n\n"
            else:
                full_message = ""
            
            # Add conversation context
            for msg in context_messages:
                role = msg["role"]
                content = msg["content"]
                if role == "user":
                    full_message += f"User: {content}\n"
                elif role == "assistant":
                    full_message += f"Assistant: {content}\n"
                elif role == "system":
                    full_message += f"System: {content}\n"
            
            # Add current user message
            full_message += f"User: {user_message}\n"
            
            # Get conversation ID for context
            conversation = conversation_manager.get_conversation(session_id)
            conversation_id = conversation.id if conversation else None
            
            # Invoke custom LLM
            response, error = self.llm_api.invoke(
                message=full_message,
                deployment_id=deployment_id,
                conversation_id=conversation_id
            )
            
            if error:
                return f"Error: {error}", conversation_id
            
            # Extract response content
            response_content = response.get("Message", "No response generated") if response else "No response generated"
            
            # Add assistant response to conversation
            conversation_manager.add_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=response_content
            )
            
            return response_content, conversation_id
            
        except Exception as e:
            logger.error(f"Error in contextual custom LLM invocation: {e}")
            return f"Error: {str(e)}", None
    
    def invoke_chat_with_context(
        self, 
        session_id: str, 
        user_message: str, 
        deployment_id: str = "text_to_sql",
        system_prompt: Optional[str] = None,
        max_context_messages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Invoke custom LLM with context and return structured response
        
        Args:
            session_id: Session identifier
            user_message: Current user message
            deployment_id: Custom deployment ID to use
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
                max_context_messages=max_context_messages,
                deployment_id=deployment_id
            )
            
            return {
                "Message": response_content,
                "ConversationId": conversation_id,
                "SessionId": session_id,
                "DeploymentId": deployment_id,
                "ContextMessages": len(conversation_manager.get_conversation_messages(session_id))
            }
            
        except Exception as e:
            logger.error(f"Error in custom chat invocation: {e}")
            return {
                "Message": f"Error: {str(e)}",
                "ConversationId": None,
                "SessionId": session_id,
                "DeploymentId": deployment_id,
                "Error": str(e)
            }

# Global contextual custom LLM service instance
contextual_custom_llm_service = ContextualCustomLLMService() 