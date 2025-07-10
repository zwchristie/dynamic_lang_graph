#!/usr/bin/env python3
"""
Example script demonstrating provider selection functionality
for the LangGraph-based text-to-SQL flow with conversation context.

This script shows how to use different LLM providers:
- OpenAI (default)
- Bedrock (AWS)
- Custom LLM (your internal provider)

Usage:
    python example_provider_selection.py
"""

import requests
import json
import time
from typing import Dict, Any, List, Optional

# API Configuration
BASE_URL = "http://localhost:8000"

def send_chat_request(
    message: str, 
    session_id: Optional[str] = None, 
    provider: str = "openai",
    system_prompt: Optional[str] = None,
    clear_context: bool = False
) -> Dict[str, Any]:
    """
    Send a chat request to the API with provider selection
    """
    url = f"{BASE_URL}/chat"
    
    payload = {
        "message": message,
        "provider": provider,
        "clear_context": clear_context
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    if system_prompt:
        payload["system_prompt"] = system_prompt
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending request: {e}")
        return {"error": str(e)}

def execute_specific_flow(
    flow_name: str,
    message: str,
    session_id: Optional[str] = None,
    provider: str = "openai",
    system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a specific flow with provider selection
    """
    url = f"{BASE_URL}/flow/{flow_name}"
    
    payload = {
        "message": message,
        "provider": provider
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    if system_prompt:
        payload["system_prompt"] = system_prompt
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error executing flow: {e}")
        return {"error": str(e)}

def get_conversation_context(session_id: str) -> Dict[str, Any]:
    """
    Get conversation context for a session
    """
    url = f"{BASE_URL}/conversation/context"
    
    payload = {
        "session_id": session_id,
        "max_messages": 10
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting conversation context: {e}")
        return {"error": str(e)}

def clear_conversation(session_id: str) -> Dict[str, Any]:
    """
    Clear conversation context for a session
    """
    url = f"{BASE_URL}/conversation/clear"
    
    payload = {
        "session_id": session_id
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error clearing conversation: {e}")
        return {"error": str(e)}

def demo_provider_comparison():
    """
    Demonstrate using different providers for the same request
    """
    print("=" * 60)
    print("PROVIDER COMPARISON DEMO")
    print("=" * 60)
    
    # Test message
    test_message = "Generate a SQL query to find all employees in the sales department with salary greater than 50000"
    
    # Test with different providers
    providers = ["openai", "bedrock", "custom"]
    
    for provider in providers:
        print(f"\n--- Testing with {provider.upper()} provider ---")
        
        # Create a unique session for each provider
        session_id = f"demo_{provider}_{int(time.time())}"
        
        # Send the same request to each provider
        result = send_chat_request(
            message=test_message,
            session_id=session_id,
            provider=provider,
            system_prompt="You are a SQL expert. Generate clear and efficient SQL queries."
        )
        
        if "error" in result:
            print(f"❌ Error with {provider}: {result['error']}")
        else:
            print(f"✅ {provider.upper()} Response:")
            print(f"   Selected Flow: {result.get('selected_flow', 'N/A')}")
            print(f"   Response: {result.get('response', 'No response')[:200]}...")
            print(f"   Session ID: {result.get('session_id')}")
            print(f"   Conversation ID: {result.get('conversation_id', 'N/A')}")

def demo_conversation_context():
    """
    Demonstrate conversation context management with custom provider
    """
    print("\n" + "=" * 60)
    print("CONVERSATION CONTEXT DEMO")
    print("=" * 60)
    
    session_id = f"context_demo_{int(time.time())}"
    
    # Conversation flow
    messages = [
        "What tables are available in the database?",
        "Show me the structure of the employees table",
        "Generate a query to find managers with more than 5 direct reports",
        "Can you modify that query to also show the department name?"
    ]
    
    print(f"Session ID: {session_id}")
    print("Starting conversation with custom provider...")
    
    for i, message in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"User: {message}")
        
        result = send_chat_request(
            message=message,
            session_id=session_id,
            provider="custom",
            system_prompt="You are a helpful SQL assistant. Maintain context from previous messages."
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"Assistant: {result.get('response', 'No response')[:300]}...")
            print(f"Selected Flow: {result.get('selected_flow', 'N/A')}")
    
    # Get conversation context
    print(f"\n--- Conversation Context ---")
    context = get_conversation_context(session_id)
    
    if "error" not in context:
        print(f"Total Messages: {len(context.get('messages', []))}")
        print(f"Summary: {context.get('summary', {})}")
        print(f"Context Size: {context.get('context_size', {})}")
        
        # Show recent messages
        print("\nRecent Messages:")
        for msg in context.get('messages', [])[-4:]:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:100]
            print(f"  {role.upper()}: {content}...")
    else:
        print(f"❌ Error getting context: {context['error']}")

def demo_flow_specific_execution():
    """
    Demonstrate executing specific flows with different providers
    """
    print("\n" + "=" * 60)
    print("FLOW-SPECIFIC EXECUTION DEMO")
    print("=" * 60)
    
    # Test different flows
    flows_and_messages = [
        ("text_to_sql", "Create a query to find all customers who made purchases in the last 30 days"),
        ("general_qa", "What are the best practices for database indexing?"),
    ]
    
    for flow_name, message in flows_and_messages:
        print(f"\n--- Testing {flow_name.upper()} flow ---")
        print(f"Message: {message}")
        
        # Test with custom provider
        result = execute_specific_flow(
            flow_name=flow_name,
            message=message,
            provider="custom",
            system_prompt=f"You are an expert in {flow_name.replace('_', ' ')}"
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Result: {result.get('result', 'No result')[:300]}...")
            print(f"   Flow: {result.get('flow_name')}")
            print(f"   Provider: {result.get('provider')}")

def demo_error_handling():
    """
    Demonstrate error handling for different scenarios
    """
    print("\n" + "=" * 60)
    print("ERROR HANDLING DEMO")
    print("=" * 60)
    
    # Test with invalid provider
    print("\n--- Testing Invalid Provider ---")
    result = send_chat_request(
        message="Test message",
        provider="invalid_provider"
    )
    
    if "error" in result:
        print(f"❌ Expected error: {result['error']}")
    else:
        print("⚠️  Unexpected: No error for invalid provider")
    
    # Test with non-existent flow
    print("\n--- Testing Non-existent Flow ---")
    result = execute_specific_flow(
        flow_name="non_existent_flow",
        message="Test message",
        provider="custom"
    )
    
    if "error" in result:
        print(f"❌ Expected error: {result['error']}")
    else:
        print("⚠️  Unexpected: No error for non-existent flow")

def main():
    """
    Main function to run all demos
    """
    print("🚀 LangGraph Provider Selection Demo")
    print("This demo shows how to use different LLM providers with conversation context")
    
    try:
        # Check if API is running
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print(f"❌ API is not running. Please start the server first.")
            print(f"   Expected URL: {BASE_URL}")
            return
        
        print(f"✅ API is running at {BASE_URL}")
        
        # Run demos
        demo_provider_comparison()
        demo_conversation_context()
        demo_flow_specific_execution()
        demo_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 Demo completed successfully!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {BASE_URL}")
        print("   Please make sure the server is running:")
        print("   uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 