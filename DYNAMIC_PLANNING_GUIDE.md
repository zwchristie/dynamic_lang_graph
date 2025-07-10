# Dynamic Planning System Guide

## Overview

The refactored system now supports dynamic execution planning where the LLM can decide which nodes to execute based on the user's request. This allows for more flexible and intelligent workflow execution.

## Key Features

### 1. Node Descriptions
Each node in a flow now has a structured description that includes:
- **Name**: Unique identifier for the node
- **Description**: What the node does
- **Inputs**: What data the node expects
- **Outputs**: What data the node produces
- **Possible Next Nodes**: Which nodes can be executed after this one
- **Conditions**: When to route to specific next nodes

### 2. LLM-Driven Planning
The system uses an LLM to analyze user requests and determine the optimal execution path through the available nodes.

### 3. Flexible Execution
Instead of always following a fixed path, the system can:
- Skip unnecessary nodes
- Choose different paths based on request type
- Handle partial workflows (e.g., just fix SQL without full generation)

## Architecture Changes

### Base Flow Class
The `BaseFlow` class now includes:

```python
@abstractmethod
def get_node_descriptions(self) -> List[NodeDescription]:
    """Get descriptions of all nodes for LLM planning"""
    pass

def plan_execution_path(self, user_message: str, current_state: Optional[Dict[str, Any]] = None) -> List[str]:
    """Use LLM to plan the execution path through nodes"""

def run_with_planning(self, state: FlowState, user_message: str) -> FlowState:
    """Run the flow with LLM-planned execution path"""
```

### Node Description Structure
```python
class NodeDescription(TypedDict):
    name: str
    description: str
    inputs: List[str]
    outputs: List[str]
    possible_next_nodes: List[str]
    conditions: Optional[Dict[str, str]]
```

## Example: Text-to-SQL Flow

The text-to-sql flow now has 10 nodes with descriptions:

1. **classify_prompt**: Analyzes if request is general or SQL-related
2. **rewrite_prompt**: Rewrites user prompt for better SQL generation
3. **get_relevant_tables**: Identifies needed database tables
4. **has_user_approved**: Human-in-the-loop table confirmation
5. **trim_relevant_tables**: Filters schema to needed columns
6. **generate_sql**: Generates SQL from natural language
7. **validate_sql**: Validates SQL correctness
8. **execute_sql**: Runs SQL and fetches results
9. **format_final_response**: Formats final response
10. **general_questions**: Handles non-SQL questions

## Usage Examples

### 1. Planning Execution Path
```python
# Plan execution for a specific request
planned_path = flow.plan_execution_path("Show me all users")
# Returns: ["classify_prompt", "rewrite_prompt", "get_relevant_tables", ...]
```

### 2. Running with Planning
```python
# Run flow with LLM-planned path
result = flow.run_with_planning(state, user_message)
```

### 3. API Usage
```python
# Chat with planning enabled
response = requests.post("/api/chat", json={
    "messages": [{"role": "user", "content": "Fix this SQL"}],
    "use_planning": True
})
```

## API Endpoints

### New Planning Endpoints

1. **GET /api/planning/flows**: Get planning info for all flows
2. **GET /api/planning/flows/{flow_name}**: Get detailed planning info for a flow
3. **POST /api/planning/plan**: Plan execution path for a request

### Updated Chat Endpoint
- **POST /api/chat**: Now supports `use_planning` parameter

## Benefits

### 1. Efficiency
- Skip unnecessary nodes (e.g., don't generate SQL if user just wants to fix existing SQL)
- Optimize execution path based on request type

### 2. Flexibility
- Handle partial workflows
- Support different request types with same flow
- Easy to add new nodes without changing existing logic

### 3. Intelligence
- LLM understands context and can make smart decisions
- Can handle edge cases and special requests
- Learns from user patterns

## Implementation Details

### Planning Process
1. **Context Gathering**: Collect node descriptions and current state
2. **LLM Analysis**: LLM analyzes user request and available nodes
3. **Path Generation**: LLM generates optimal execution path
4. **Execution**: Follow planned path through the graph

### State Management
- Planned path stored in `state["metadata"]["planned_execution_path"]`
- Current position tracked in `state["metadata"]["current_path_index"]`
- Original graph structure preserved for fallback

### Error Handling
- If planning fails, falls back to full graph execution
- Graceful degradation to original behavior
- Comprehensive error logging

## Migration from Original System

### What Changed
1. **Node Descriptions**: Added `get_node_descriptions()` method to all flows
2. **Planning Methods**: Added planning capabilities to base class
3. **API Updates**: New endpoints for planning functionality
4. **Schema Updates**: Added planning-related fields to request/response models

### What Stayed the Same
1. **Graph Structure**: Original graph building logic preserved
2. **Node Logic**: Individual node implementations unchanged
3. **State Management**: Core state structure maintained
4. **Error Handling**: Existing error handling preserved

## Future Enhancements

### 1. Learning from Execution
- Track successful paths for similar requests
- Use historical data to improve planning

### 2. Dynamic Node Creation
- Allow LLM to suggest new nodes
- Automatic node generation based on patterns

### 3. Multi-Flow Planning
- Plan across multiple flows
- Intelligent flow selection and combination

### 4. Advanced Conditions
- More sophisticated routing logic
- Context-aware node selection

## Testing

Use the provided example script to test the system:

```bash
python example_dynamic_planning.py
```

This will demonstrate:
- Getting flow planning information
- Planning execution paths
- Testing actual execution with planning
- Comparing planned vs expected paths

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for LLM planning
- `OPENAI_MODEL`: Model to use for planning (default: gpt-4)

### Planning Parameters
- `temperature`: Controls planning creativity (default: 0.3)
- `max_retries`: Number of planning attempts (default: 3)
- `fallback_enabled`: Whether to fallback to full execution (default: true)

## Troubleshooting

### Common Issues

1. **Planning Fails**: Check OpenAI API key and model availability
2. **Unexpected Paths**: Review node descriptions for clarity
3. **Performance Issues**: Consider caching planning results
4. **State Conflicts**: Ensure state structure is consistent

### Debug Mode
Enable debug logging to see planning decisions:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Conclusion

The dynamic planning system provides a more intelligent and flexible approach to workflow execution. By allowing the LLM to understand the available nodes and plan optimal execution paths, the system can handle a wider variety of requests more efficiently.

The system maintains backward compatibility while adding powerful new capabilities for intelligent workflow orchestration. 