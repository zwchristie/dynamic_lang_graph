#!/usr/bin/env python3
"""
Example usage of the conversation context management system.
This script demonstrates how conversation context is maintained across multiple requests.
"""

import sys
import os
import requests
import json
import time
from typing import List, Optional

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.schemas import Message, MessageRole, ChatRequest

class ConversationContextClient:
    """Client for testing conversation context management"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    def chat(self, message: str, flow_name: Optional[str] = None) -> dict:
        """Send a chat message to the system"""
        messages = [Message(role=MessageRole.USER, content=message)]
        
        request_data = ChatRequest(
            messages=messages,
            session_id=self.session_id,
            flow_name=flow_name,
            use_planning=True
        )
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=request_data.dict()
        )
        
        if response.status_code == 200:
            result = response.json()
            self.session_id = result["session_id"]
            return result
        else:
            raise Exception(f"Chat request failed: {response.text}")
    
    def get_conversation_context(self, session_id: str) -> dict:
        """Get conversation context for a session"""
        response = requests.get(f"{self.base_url}/api/conversations/{session_id}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get conversation context: {response.text}")
    
    def clear_conversation_context(self, session_id: str) -> dict:
        """Clear conversation context for a session"""
        response = requests.delete(f"{self.base_url}/api/conversations/{session_id}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to clear conversation context: {response.text}")

def demonstrate_conversation_context():
    """Demonstrate conversation context management"""
    client = ConversationContextClient()
    
    print("=== Conversation Context Management Demo ===\n")
    
    # Test 1: Basic conversation with context
    print("1. Testing basic conversation with context...")
    
    messages = [
        "Hello, I'm working on a SQL project",
        "Can you help me write a query to find all users?",
        "Actually, I only want users who signed up this year",
        "Can you modify that query to also show their email addresses?"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"User: {message}")
        
        try:
            result = client.chat(message)
            print(f"Assistant: {result['response'][:100]}...")
            print(f"Session ID: {result['session_id']}")
            print(f"Flow used: {result['flow_name']}")
            
            # Get conversation context
            context = client.get_conversation_context(result['session_id'])
            context_info = context['conversation_context']
            print(f"Context messages: {context_info['context_size']['message_count']}")
            print(f"Context usage: {context_info['context_size']['context_usage_percent']:.1f}%")
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Test 2: Context-aware follow-up questions
    print("\n\n2. Testing context-aware follow-up questions...")
    
    follow_up_messages = [
        "What was the previous query we discussed?",
        "Can you explain what that query does?",
        "How would I modify it to include user roles?",
        "Show me the SQL syntax for that modification"
    ]
    
    for i, message in enumerate(follow_up_messages, 1):
        print(f"\n--- Follow-up {i} ---")
        print(f"User: {message}")
        
        try:
            result = client.chat(message)
            print(f"Assistant: {result['response'][:150]}...")
            
            # Show context information
            context = client.get_conversation_context(result['session_id'])
            context_info = context['conversation_context']
            print(f"Context size: {context_info['context_size']['message_count']} messages")
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Test 3: Context clearing and restart
    print("\n\n3. Testing context clearing...")
    
    try:
        # Clear the conversation context
        print("Clearing conversation context...")
        clear_result = client.clear_conversation_context(client.session_id)
        print(f"Clear result: {clear_result['message']}")
        
        # Try a new conversation
        print("\nStarting new conversation...")
        result = client.chat("Hello, I'm starting fresh. Can you help me with SQL?")
        print(f"Assistant: {result['response'][:100]}...")
        
        # Check context
        context = client.get_conversation_context(result['session_id'])
        context_info = context['conversation_context']
        print(f"New context messages: {context_info['context_size']['message_count']}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Different conversation types
    print("\n\n4. Testing different conversation types...")
    
    # Create a new session for general questions
    client.session_id = None
    
    general_messages = [
        "What is the capital of France?",
        "Tell me more about its history",
        "What are some popular tourist attractions there?",
        "How does the weather compare to other European capitals?"
    ]
    
    for i, message in enumerate(general_messages, 1):
        print(f"\n--- General Question {i} ---")
        print(f"User: {message}")
        
        try:
            result = client.chat(message)
            print(f"Assistant: {result['response'][:100]}...")
            print(f"Flow used: {result['flow_name']}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n=== Demo Complete ===")

def demonstrate_context_persistence():
    """Demonstrate context persistence across requests"""
    client = ConversationContextClient()
    
    print("\n=== Context Persistence Demo ===\n")
    
    # Simulate a conversation that spans multiple requests
    conversation_steps = [
        {
            "message": "I need help with a database query",
            "expected_context": "Should establish SQL context"
        },
        {
            "message": "I have a users table with columns: id, name, email, created_at",
            "expected_context": "Should remember table structure"
        },
        {
            "message": "I want to find users who signed up in the last 30 days",
            "expected_context": "Should use previous context to build query"
        },
        {
            "message": "Actually, make it users who signed up this year",
            "expected_context": "Should modify previous query"
        },
        {
            "message": "Can you also show their total orders?",
            "expected_context": "Should extend query with additional context"
        }
    ]
    
    for i, step in enumerate(conversation_steps, 1):
        print(f"\n--- Step {i} ---")
        print(f"User: {step['message']}")
        print(f"Expected: {step['expected_context']}")
        
        try:
            result = client.chat(step['message'])
            print(f"Assistant: {result['response'][:120]}...")
            
            # Show context information
            context = client.get_conversation_context(result['session_id'])
            context_info = context['conversation_context']
            print(f"Context: {context_info['context_size']['message_count']} messages, "
                  f"{context_info['context_size']['context_usage_percent']:.1f}% usage")
            
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n=== Persistence Demo Complete ===")

if __name__ == "__main__":
    demonstrate_conversation_context()
    demonstrate_context_persistence() 