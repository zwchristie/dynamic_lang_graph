from typing import Dict, Any, List, Optional
from ..flows.base import FLOW_REGISTRY
from ..models.schemas import FlowInfo, FlowRegistration

class FlowRegistryService:
    """Service for managing flow registration and discovery"""
    
    def __init__(self):
        self.registry = FLOW_REGISTRY
    
    def register_flow(self, flow_registration: FlowRegistration) -> bool:
        """Register a new flow dynamically"""
        try:
            # This would typically involve dynamic class loading
            # For now, we'll just validate the registration
            if flow_registration.name in self.registry:
                return False  # Flow already exists
            
            # In a real implementation, you would dynamically load the flow class
            # and add it to the registry
            return True
        except Exception as e:
            print(f"Error registering flow: {e}")
            return False
    
    def get_all_flows(self) -> List[FlowInfo]:
        """Get information about all registered flows"""
        flow_info = []
        
        for name, flow_class in self.registry.items():
            try:
                instance = flow_class()
                flow_info.append(FlowInfo(
                    name=name,
                    description=instance.flow_description,
                    parameters=None  # Could be extended to include flow parameters
                ))
            except Exception as e:
                print(f"Error getting info for flow {name}: {e}")
                continue
        
        return flow_info
    
    def get_flow_by_name(self, name: str) -> Optional[FlowInfo]:
        """Get information about a specific flow"""
        if name not in self.registry:
            return None
        
        try:
            flow_class = self.registry[name]
            instance = flow_class()
            return FlowInfo(
                name=name,
                description=instance.flow_description,
                parameters=None
            )
        except Exception as e:
            print(f"Error getting info for flow {name}: {e}")
            return None
    
    def list_flow_names(self) -> List[str]:
        """Get list of all registered flow names"""
        return list(self.registry.keys())
    
    def flow_exists(self, name: str) -> bool:
        """Check if a flow exists"""
        return name in self.registry
    
    def get_flow_count(self) -> int:
        """Get total number of registered flows"""
        return len(self.registry)
    
    def get_flows_by_category(self, category: Optional[str] = None) -> List[FlowInfo]:
        """Get flows filtered by category (future enhancement)"""
        # For now, return all flows
        # In the future, flows could have categories
        return self.get_all_flows()
    
    def validate_flow_name(self, name: str) -> bool:
        """Validate if a flow name is valid"""
        import re
        # Flow names should be lowercase, alphanumeric with underscores
        pattern = r'^[a-z][a-z0-9_]*$'
        return bool(re.match(pattern, name))
    
    def get_flow_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered flows"""
        total_flows = len(self.registry)
        flow_names = list(self.registry.keys())
        
        return {
            "total_flows": total_flows,
            "flow_names": flow_names,
            "categories": {
                "text_to_sql": len([f for f in flow_names if "sql" in f.lower()]),
                "general_qa": len([f for f in flow_names if "qa" in f.lower() or "general" in f.lower()]),
                "other": len([f for f in flow_names if "sql" not in f.lower() and "qa" not in f.lower() and "general" not in f.lower()])
            }
        } 