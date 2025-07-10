#!/usr/bin/env python3
"""
Example usage of the dynamic planning system.
This script demonstrates how the LLM can plan execution paths through nodes.
"""

import sys
import os
import requests
import json
from typing import List, Optional

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.schemas import Message, MessageRole, ChatRequest

class DynamicPlanningClient:
    """Client for testing the dynamic planning system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    def get_flow_planning_info(self, flow_name: str) -> dict:
        """Get detailed planning information for a flow"""
        response = requests.get(f"{self.base_url}/api/planning/flows/{flow_name}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get flow planning info: {response.text}")
    
    def plan_execution(self, flow_name: str, user_message: str, current_state: Optional[dict] = None) -> dict:
        """Plan execution path for a specific request"""
        request_data = {
            "flow_name": flow_name,
            "user_message": user_message,
            "current_state": current_state
        }
        
        response = requests.post(
            f"{self.base_url}/api/planning/plan",
            json=request_data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to plan execution: {response.text}")
    
    def chat_with_planning(self, message: str, flow_name: Optional[str] = None, use_planning: bool = True) -> dict:
        """Send a chat message with planning enabled"""
        messages = [Message(role=MessageRole.USER, content=message)]
        
        request_data = ChatRequest(
            messages=messages,
            session_id=self.session_id,
            flow_name=flow_name,
            use_planning=use_planning
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
    
    def get_session_info(self, session_id: str) -> dict:
        """Get information about a session"""
        response = requests.get(f"{self.base_url}/api/sessions/{session_id}")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get session info: {response.text}")

def demonstrate_dynamic_planning():
    """Demonstrate the dynamic planning system"""
    client = DynamicPlanningClient()
    
    print("=== Dynamic Planning System Demo ===\n")
    
    # 1. Get planning information for text-to-sql flow
    print("1. Getting flow planning information...")
    try:
        planning_info = client.get_flow_planning_info("text_to_sql")
        print(f"Flow: {planning_info['name']}")
        print(f"Description: {planning_info['description']}")
        print(f"Number of nodes: {len(planning_info['nodes'])}")
        print("\nAvailable nodes:")
        for node in planning_info['nodes']:
            print(f"  - {node['name']}: {node['description']}")
            print(f"    Inputs: {', '.join(node['inputs'])}")
            print(f"    Outputs: {', '.join(node['outputs'])}")
            print(f"    Next nodes: {', '.join(node['possible_next_nodes'])}")
        print()
    except Exception as e:
        print(f"Error getting planning info: {e}")
        return
    
    # 2. Plan execution for different types of requests
    test_cases = [
        {
            "name": "General Question",
            "message": "What is the weather like today?",
            "expected_nodes": ["classify_prompt", "general_questions", "format_final_response"]
        },
        {
            "name": "Simple SQL Query",
            "message": "Show me all users from the users table",
            "expected_nodes": ["classify_prompt", "rewrite_prompt", "get_relevant_tables", "has_user_approved", "trim_relevant_tables", "generate_sql", "validate_sql", "execute_sql", "format_final_response"]
        },
        {
            "name": "SQL Fix Request",
            "message": "Fix this SQL query: SELECT * FROM users WHERE name = 'John'",
            "expected_nodes": ["classify_prompt", "rewrite_prompt", "get_relevant_tables", "has_user_approved", "trim_relevant_tables", "generate_sql", "validate_sql", "execute_sql", "format_final_response"]
        }
    ]
    
    print("2. Planning execution paths for different requests...")
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        print(f"Message: {test_case['message']}")
        
        try:
            plan = client.plan_execution("text_to_sql", test_case['message'])
            print(f"Planned path: {plan['planned_path']}")
            print(f"Node count: {plan['node_count']}")
            
            # Compare with expected
            expected = test_case['expected_nodes']
            actual = plan['planned_path']
            if actual == expected:
                print("✅ Path matches expected")
            else:
                print("⚠️  Path differs from expected")
                print(f"Expected: {expected}")
                print(f"Actual: {actual}")
                
        except Exception as e:
            print(f"Error planning execution: {e}")
    
    # 3. Test actual execution with planning
    print("\n3. Testing actual execution with planning...")
    test_messages = [
        "What is the capital of France?",
        "Show me all users from the database",
        "Fix this SQL: SELECT * FROM users"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        print(f"Message: {message}")
        
        try:
            result = client.chat_with_planning(message, use_planning=True)
            print(f"Response: {result['response'][:100]}...")
            print(f"Flow used: {result['flow_name']}")
            print(f"Planned path: {result.get('planned_path', [])}")
            print(f"Session ID: {result['session_id']}")
            
            # Get session details
            session_info = client.get_session_info(result['session_id'])
            print(f"Session metadata keys: {list(session_info.get('metadata', {}).keys())}")
            
        except Exception as e:
            print(f"Error in chat: {e}")
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    demonstrate_dynamic_planning() 