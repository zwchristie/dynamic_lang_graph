#!/usr/bin/env python3
"""
Test script to verify the agentic workflow system setup.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that all modules can be imported successfully"""
    print("Testing imports...")
    
    try:
        from app.core.config import settings
        print("✓ Configuration imported successfully")
        
        from app.models.schemas import ChatRequest, Message, MessageRole
        print("✓ Schemas imported successfully")
        
        from app.flows.base import FLOW_REGISTRY, get_all_flows, get_flow_by_name
        print("✓ Flow base imported successfully")
        
        from app.flows.general_qa import GeneralQAFlow
        print("✓ General QA flow imported successfully")
        
        from app.flows.text_to_sql import TextToSQLFlow
        print("✓ Text-to-SQL flow imported successfully")
        
        from app.services.orchestrator import OrchestratorService
        print("✓ Orchestrator service imported successfully")
        
        from app.services.flow_registry import FlowRegistryService
        print("✓ Flow registry service imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_flow_registration():
    """Test that flows are properly registered"""
    print("\nTesting flow registration...")
    
    try:
        from app.flows.base import FLOW_REGISTRY
        
        print(f"Registered flows: {list(FLOW_REGISTRY.keys())}")
        
        if "general_qa" in FLOW_REGISTRY:
            print("✓ General QA flow registered")
        else:
            print("✗ General QA flow not registered")
            return False
            
        if "text_to_sql" in FLOW_REGISTRY:
            print("✓ Text-to-SQL flow registered")
        else:
            print("✗ Text-to-SQL flow not registered")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Flow registration error: {e}")
        return False

def test_flow_instances():
    """Test that flow instances can be created"""
    print("\nTesting flow instances...")
    
    try:
        from app.flows.base import get_all_flows
        
        flows = get_all_flows()
        print(f"Created {len(flows)} flow instances")
        
        for flow in flows:
            print(f"  - {flow.flow_name}: {flow.flow_description}")
        
        return True
        
    except Exception as e:
        print(f"✗ Flow instance error: {e}")
        return False

def test_orchestrator():
    """Test the orchestrator service"""
    print("\nTesting orchestrator service...")
    
    try:
        from app.services.orchestrator import OrchestratorService
        
        orchestrator = OrchestratorService()
        
        # Test flow info
        flow_info = orchestrator.get_flow_info()
        print(f"Orchestrator found {len(flow_info)} flows")
        
        for flow in flow_info:
            print(f"  - {flow['name']}: {flow['description']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Orchestrator error: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from app.core.config import settings
        
        print(f"App name: {settings.app_name}")
        print(f"OpenAI model: {settings.openai_model}")
        print(f"Database URL: {settings.database_url}")
        print(f"Debug mode: {settings.debug}")
        print(f"Max iterations: {settings.max_iterations}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def main():
    """Run all tests"""
    print("Agentic Workflow System - Setup Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_flow_registration,
        test_flow_instances,
        test_orchestrator,
        test_configuration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("1. Copy env.example to .env and set your OpenAI API key")
        print("2. Run: uvicorn app.main:app --reload")
        print("3. Visit http://localhost:8000/docs for API documentation")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 