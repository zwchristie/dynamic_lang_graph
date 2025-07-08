#!/usr/bin/env python3
"""
Example usage of the agentic workflow system.
This script demonstrates how to interact with the system programmatically.
"""

import sys
import os
import requests
import json
from typing import List

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.schemas import Message, MessageRole, ChatRequest

class AgenticWorkflowClient:
    """Client for interacting with the agentic workflow system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    def chat(self, message: str, flow_name: str = None) -> dict:
        """Send a chat message to the system"""
        
        # Create messages list
        messages = [Message(role=MessageRole.USER, content=message)]
        
        # Create request
        request_data = ChatRequest(
            messages=messages,
            session_id=self.session_id,
            flow_name=flow_name
        )
        
        # Send request
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
    
    def get_flows(self) -> List[dict]:
        """Get all available flows"""
        response = requests.get(f"{self.base_url}/api/flows")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get flows: {response.text}")
    
    def validate_step(self, validation_type: str, data: dict, user_response: bool) -> dict:
        """Send a validation response for human-in-the-loop steps"""
        
        request_data = {
            "session_id": self.session_id,
            "validation_type": validation_type,
            "data": data,
            "user_response": user_response
        }
        
        response = requests.post(
            f"{self.base_url}/api/validate",
            json=request_data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Validation request failed: {response.text}")

def example_general_qa():
    """Example of using the general QA flow"""
    print("=== General QA Example ===")
    
    client = AgenticWorkflowClient()
    
    # Get available flows
    flows = client.get_flows()
    print(f"Available flows: {[f['name'] for f in flows]}")
    
    # Ask a general question
    question = "What is the capital of France and what are some interesting facts about it?"
    
    print(f"\nAsking: {question}")
    result = client.chat(question)
    
    print(f"Flow used: {result['flow_name']}")
    print(f"Response: {result['response']}")

def example_text_to_sql():
    """Example of using the text-to-SQL flow"""
    print("\n=== Text-to-SQL Example ===")
    
    client = AgenticWorkflowClient()
    
    # Ask for SQL generation
    sql_request = "Show me all users who have placed orders with a total value greater than $100"
    
    print(f"\nRequesting SQL for: {sql_request}")
    result = client.chat(sql_request, flow_name="text_to_sql")
    
    print(f"Flow used: {result['flow_name']}")
    print(f"Response: {result['response']}")

def example_flow_discovery():
    """Example of how the orchestrator discovers and uses flows"""
    print("\n=== Flow Discovery Example ===")
    
    client = AgenticWorkflowClient()
    
    # Test different types of requests to see which flow gets selected
    requests = [
        "What is the weather like today?",
        "Generate a SQL query to find all customers from New York",
        "How do I implement a binary search algorithm?",
        "Create a SQL query to calculate the average order value by month"
    ]
    
    for request in requests:
        print(f"\nRequest: {request}")
        result = client.chat(request)
        print(f"Selected flow: {result['flow_name']}")
        print(f"Response preview: {result['response'][:100]}...")

def example_validation_workflow():
    """Example of human-in-the-loop validation workflow"""
    print("\n=== Validation Workflow Example ===")
    
    client = AgenticWorkflowClient()
    
    # This would typically be triggered by the text-to-SQL flow
    # when it needs human validation for table selection
    
    # Simulate a table validation request
    table_data = {
        "tables": [
            {"name": "users", "reasoning": "Need user information"},
            {"name": "orders", "reasoning": "Need order details"}
        ]
    }
    
    print("Simulating table validation request...")
    validation_result = client.validate_step(
        validation_type="table_selection",
        data=table_data,
        user_response=True  # User approves the table selection
    )
    
    print(f"Validation result: {validation_result}")

def main():
    """Run all examples"""
    print("Agentic Workflow System - Usage Examples")
    print("=" * 50)
    
    try:
        # Check if the server is running
        response = requests.get("http://localhost:8000/health")
        if response.status_code != 200:
            print("❌ Server is not running. Please start the server first:")
            print("   uvicorn app.main:app --reload")
            return
        
        print("✅ Server is running!")
        
        # Run examples
        example_general_qa()
        example_text_to_sql()
        example_flow_discovery()
        example_validation_workflow()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server.")
        print("Please make sure the server is running:")
        print("   uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Error running examples: {e}")

if __name__ == "__main__":
    main() 