from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from .base import BaseFlow, FlowState, flow, NodeDescription
from ..core.config import settings
from ..core.database import get_table_info
import json
import re
import logging

logger = logging.getLogger(__name__)

@flow(name="text_to_sql", description="Convert natural language to SQL queries with validation and human-in-the-loop steps")
class TextToSQLFlow(BaseFlow):
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            api_key=settings.openai_api_key
        )
        self.table_info = get_table_info()
        super().__init__()
    
    def get_node_descriptions(self) -> List[NodeDescription]:
        """Get descriptions of all nodes for LLM planning"""
        return [
            {
                "name": "classify_prompt",
                "description": "Analyzes user input to determine if it's a general question or SQL-related request",
                "inputs": ["user_message"],
                "outputs": ["classification"],
                "possible_next_nodes": ["general_questions", "rewrite_prompt"],
                "conditions": {
                    "general": "general_questions",
                    "text_to_sql": "rewrite_prompt"
                }
            },
            {
                "name": "rewrite_prompt",
                "description": "Rewrites user prompt with additional context for better SQL generation",
                "inputs": ["user_message"],
                "outputs": ["rewritten_prompt"],
                "possible_next_nodes": ["get_relevant_tables"],
                "conditions": None
            },
            {
                "name": "get_relevant_tables",
                "description": "Identifies which database tables are needed for the SQL query",
                "inputs": ["rewritten_prompt", "database_schema"],
                "outputs": ["relevant_tables"],
                "possible_next_nodes": ["has_user_approved"],
                "conditions": None
            },
            {
                "name": "has_user_approved",
                "description": "Human-in-the-loop step for table confirmation (placeholder)",
                "inputs": ["relevant_tables"],
                "outputs": ["user_approved", "relevant_schema"],
                "possible_next_nodes": ["trim_relevant_tables", "get_relevant_tables"],
                "conditions": {
                    "approved": "trim_relevant_tables",
                    "rejected": "get_relevant_tables"
                }
            },
            {
                "name": "trim_relevant_tables",
                "description": "Filters schema to only include columns needed for the query",
                "inputs": ["rewritten_prompt", "relevant_schema"],
                "outputs": ["trimmed_schema"],
                "possible_next_nodes": ["generate_sql"],
                "conditions": None
            },
            {
                "name": "generate_sql",
                "description": "Generates SQL query from natural language and schema",
                "inputs": ["rewritten_prompt", "relevant_schema"],
                "outputs": ["generated_sql"],
                "possible_next_nodes": ["validate_sql"],
                "conditions": None
            },
            {
                "name": "validate_sql",
                "description": "Validates generated SQL for correctness and relevance",
                "inputs": ["generated_sql", "user_message", "relevant_schema"],
                "outputs": ["sql_valid"],
                "possible_next_nodes": ["execute_sql", "format_final_response", "generate_sql"],
                "conditions": {
                    "valid": "execute_sql",
                    "invalid": "generate_sql",
                    "no_execution_needed": "format_final_response"
                }
            },
            {
                "name": "execute_sql",
                "description": "Executes the SQL query and fetches results",
                "inputs": ["generated_sql"],
                "outputs": ["executed_sql", "sql_error"],
                "possible_next_nodes": ["format_final_response", "generate_sql"],
                "conditions": {
                    "success": "format_final_response",
                    "error": "generate_sql"
                }
            },
            {
                "name": "format_final_response",
                "description": "Formats the final response with results and metadata",
                "inputs": ["final_llm_message", "executed_sql", "reasoning_steps"],
                "outputs": ["formatted_response"],
                "possible_next_nodes": ["END"],
                "conditions": None
            },
            {
                "name": "general_questions",
                "description": "Handles general questions that don't require SQL",
                "inputs": ["user_message"],
                "outputs": ["final_llm_message"],
                "possible_next_nodes": ["format_final_response"],
                "conditions": None
            }
        ]
    
    def _build_graph(self) -> StateGraph:
        """Build the comprehensive text-to-SQL graph with all validation steps"""
        
        workflow = StateGraph(FlowState)
        
        # Add nodes
        workflow.add_node("classify_prompt", self._classify_prompt)
        workflow.add_node("rewrite_prompt", self._rewrite_prompt)
        workflow.add_node("get_relevant_tables", self._get_relevant_tables)
        workflow.add_node("has_user_approved", self._has_user_approved)
        workflow.add_node("trim_relevant_tables", self._trim_relevant_tables)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("validate_sql", self._validate_sql)
        workflow.add_node("execute_sql", self._execute_sql)
        workflow.add_node("format_final_response", self._format_final_response)
        workflow.add_node("general_questions", self._ask_general_question)
        
        # Set entry point
        workflow.set_entry_point("classify_prompt")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "classify_prompt",
            self._classify_prompt_edge,
            {
                "general_questions": "general_questions",
                "rewrite_prompt": "rewrite_prompt"
            }
        )
        
        workflow.add_conditional_edges(
            "has_user_approved",
            self._table_confirmation_from_user_edge,
            {
                "trim_relevant_tables": "trim_relevant_tables",
                "get_relevant_tables": "get_relevant_tables"
            }
        )
        
        workflow.add_conditional_edges(
            "validate_sql",
            self._validate_edge,
            {
                "execute_sql": "execute_sql",
                "format_final_response": "format_final_response",
                "generate_sql": "generate_sql"
            }
        )
        
        workflow.add_conditional_edges(
            "execute_sql",
            self._sql_executed_edge,
            {
                "format_final_response": "format_final_response",
                "generate_sql": "generate_sql"
            }
        )
        
        # Add regular edges
        workflow.add_edge("rewrite_prompt", "get_relevant_tables")
        workflow.add_edge("get_relevant_tables", "has_user_approved")
        workflow.add_edge("trim_relevant_tables", "generate_sql")
        workflow.add_edge("generate_sql", "validate_sql")
        workflow.add_edge("general_questions", "format_final_response")
        workflow.add_edge("format_final_response", END)
        
        return workflow
    
    def _add_reasoning_step(self, state: FlowState, step: str) -> None:
        """Add a reasoning step to the state"""
        if "reasoning_steps" not in state["metadata"]:
            state["metadata"]["reasoning_steps"] = []
        state["metadata"]["reasoning_steps"].append(step)
    
    def _classify_prompt(self, state: FlowState) -> FlowState:
        """Classify user prompt as 'general' or 'text_to_sql'"""
        user_message = self.get_last_user_message(state) or ""
        logger.info("Classifying Prompt: %s", user_message)
        
        classification_prompt = f"""
        Classify the prompt below as only 'general' or 'text_to_sql'.
        
        Prompt: {user_message}
        
        Return only: general or text_to_sql
        """
        
        response = self.llm.invoke([HumanMessage(content=classification_prompt)])
        classification = str(response.content).strip().lower()
        
        # Ensure classification is one of the allowed values
        if classification in ["general", "text_to_sql"]:
            state["metadata"]["classification"] = classification
        else:
            state["metadata"]["classification"] = "general"  # Default to general
        
        state["current_step"] = "classify_prompt"
        return state
    
    def _classify_prompt_edge(self, state: FlowState) -> str:
        """Route based on classification"""
        classification = state["metadata"].get("classification", "general")
        return "general_questions" if classification == "general" else "rewrite_prompt"
    
    def _rewrite_prompt(self, state: FlowState) -> FlowState:
        """Rewrite prompt with extra metadata for SQL generation"""
        user_message = self.get_last_user_message(state) or ""
        self._add_reasoning_step(state, "Rewriting prompt")
        
        # Create a system prompt for SQL generation
        sql_system_prompt = """
        You are a SQL expert. When given a natural language query, you should:
        1. Understand the user's intent
        2. Identify the relevant database tables and columns
        3. Generate accurate SQL queries
        4. Provide clear explanations
        
        Always return valid SQL syntax and explain your reasoning.
        """
        
        rewrite_prompt = f"""
        {sql_system_prompt}
        
        Original user request: {user_message}
        
        Please rewrite this request to be more specific for SQL generation, 
        including any clarifying details that would help generate accurate SQL.
        """
        
        response = self.llm.invoke([HumanMessage(content=rewrite_prompt)])
        rewritten_prompt = str(response.content).strip()
        
        self._add_reasoning_step(state, f"Rewritten Prompt: {rewritten_prompt}")
        logger.info("Rewritten Prompt: %s", rewritten_prompt)
        
        state["metadata"]["rewritten_prompt"] = rewritten_prompt
        state["current_step"] = "rewrite_prompt"
        
        return state
    
    def _get_relevant_tables(self, state: FlowState) -> FlowState:
        """Identify DB tables likely needed"""
        user_message = state["metadata"].get("rewritten_prompt") or self.get_last_user_message(state) or ""
        
        # Get concise schema information
        available_tables = [table["name"] for table in self.table_info["tables"]]
        table_schemas = {}
        for table in self.table_info["tables"]:
            columns = [col["name"] for col in table.get("columns", [])]
            table_schemas[table["name"]] = columns
        
        concise_schema = json.dumps(table_schemas, indent=2)
        
        table_identification_prompt = f"""
        Based on the user request, identify the relevant database tables and their purpose.
        
        User request: {user_message}
        Available tables and their columns: {concise_schema}
        
        Return in JSON format:
        {{
            "tables": ["table1", "table2"],
            "reasoning": "Why these tables are needed"
        }}
        """
        
        response = self.llm.invoke([HumanMessage(content=table_identification_prompt)])
        
        try:
            content = str(response.content) if response.content else "{}"
            result = json.loads(content)
            tables = result.get("tables", [])
            self._add_reasoning_step(state, f"Identified Relevant Tables: {tables}")
        except:
            logger.info("Table identification error")
            tables = []
        
        state["metadata"]["relevant_tables"] = json.dumps(tables)
        state["current_step"] = "get_relevant_tables"
        
        return state
    
    def _has_user_approved(self, state: FlowState) -> FlowState:
        """Human-in-the-loop confirmation of table list (placeholder)"""
        # TODO: integrate real UI approval
        relevant_tables = state["metadata"].get("relevant_tables", "[]")
        try:
            tables = json.loads(relevant_tables)
        except:
            tables = []
        
        # Get relevant schema for identified tables
        relevant_schema = {}
        for table_name in tables:
            for table in self.table_info["tables"]:
                if table["name"] == table_name:
                    relevant_schema[table_name] = [col["name"] for col in table.get("columns", [])]
                    break
        
        self._add_reasoning_step(state, f"User approved tables: {tables}")
        
        state["metadata"]["user_approved"] = True  # Placeholder - should be user input
        state["metadata"]["relevant_schema"] = relevant_schema
        state["current_step"] = "has_user_approved"
        
        return state
    
    def _table_confirmation_from_user_edge(self, state: FlowState) -> str:
        """Route based on user approval"""
        return "trim_relevant_tables" if state["metadata"].get("user_approved") else "get_relevant_tables"
    
    def _trim_relevant_tables(self, state: FlowState) -> FlowState:
        """Reduce metadata to only needed columns"""
        user_message = state["metadata"].get("rewritten_prompt") or self.get_last_user_message(state) or ""
        relevant_schema = state["metadata"].get("relevant_schema", {})
        
        trim_prompt = f"""
        Based on the user request, identify only the relevant columns from the schema.
        
        User request: {user_message}
        Available schema: {json.dumps(relevant_schema, indent=2)}
        
        Return only the relevant columns in JSON format:
        {{
            "table_name": ["column1", "column2"]
        }}
        """
        
        response = self.llm.invoke([HumanMessage(content=trim_prompt)])
        
        try:
            trimmed_schema = json.loads(str(response.content))
            self._add_reasoning_step(state, f"Trimmed schema: {trimmed_schema}")
        except:
            logger.info("Table trim error")
            trimmed_schema = relevant_schema
        
        state["metadata"]["relevant_schema"] = trimmed_schema
        state["current_step"] = "trim_relevant_tables"
        
        return state
    
    def _generate_sql(self, state: FlowState) -> FlowState:
        """Generate SQL query"""
        user_message = state["metadata"].get("rewritten_prompt") or self.get_last_user_message(state) or ""
        schema = state["metadata"].get("relevant_schema", {})
        
        if not schema:
            state["metadata"]["generated_sql"] = ""
            state["current_step"] = "generate_sql"
            return state
        
        retries = state["metadata"].get("sql_failed_times", 0)
        
        if retries == 0 and not state["metadata"].get("final_sql_execution_error") and not state["metadata"].get("empty_sql_return"):
            # First attempt
            sql_prompt = f"""
            Generate a SQL query based on the user request.
            
            User request: {user_message}
            Available schema: {json.dumps(schema, indent=2)}
            
            Return only the SQL query, no additional text or explanations.
            """
        else:
            # Retry with error context
            error_msg = state["metadata"].get("final_sql_execution_error", "")
            empty_return = state["metadata"].get("empty_sql_return", False)
            previous_sql = state["metadata"].get("generated_sql", "")
            
            sql_prompt = f"""
            Fix the SQL query based on the error or user feedback.
            
            User request: {user_message}
            Available schema: {json.dumps(schema, indent=2)}
            Previous SQL: {previous_sql}
            Error: {error_msg}
            Empty return: {empty_return}
            
            Return only the corrected SQL query, no additional text.
            """
        
        response = self.llm.invoke([HumanMessage(content=sql_prompt)])
        sql_query = str(response.content).strip()
        
        # Clean up SQL formatting
        sql_query = re.sub(r'```sql\s*', '', sql_query)
        sql_query = re.sub(r'\s*```', '', sql_query)
        
        self._add_reasoning_step(state, f"Generated SQL: {sql_query}")
        
        state["metadata"]["generated_sql"] = sql_query
        state["metadata"]["final_llm_message"] = str(response.content)
        state["current_step"] = "generate_sql"
        
        return state
    
    def _validate_sql(self, state: FlowState) -> FlowState:
        """Validate generated SQL"""
        user_message = state["metadata"].get("rewritten_prompt") or self.get_last_user_message(state) or ""
        sql_query = state["metadata"].get("generated_sql", "")
        schema = state["metadata"].get("relevant_schema", {})
        
        validate_prompt = f"""
        Validate the SQL query for correctness and relevance to the user request.
        
        User request: {user_message}
        Generated SQL: {sql_query}
        Available schema: {json.dumps(schema, indent=2)}
        
        Check for:
        1. Syntax correctness
        2. Relevance to user request
        3. Proper table and column usage
        
        Return only: VALID or INVALID
        """
        
        response = self.llm.invoke([HumanMessage(content=validate_prompt)])
        validation_result = str(response.content).strip().upper()
        
        is_valid = validation_result == "VALID"
        
        if is_valid:
            logger.info("FINAL SQL QUERY: %s", sql_query)
        
        state["metadata"]["sql_valid"] = is_valid
        state["current_step"] = "validate_sql"
        
        return state
    
    def _validate_edge(self, state: FlowState) -> str:
        """Route based on SQL validation"""
        if state["metadata"].get("sql_valid"):
            return "execute_sql" if state["metadata"].get("query_required", True) else "format_final_response"
        return "generate_sql"
    
    def _execute_sql(self, state: FlowState) -> FlowState:
        """Run the SQL and fetch results (mock implementation)"""
        if not state["metadata"].get("sql_valid"):
            state["metadata"]["executed_sql"] = None
            state["current_step"] = "execute_sql"
            return state
        
        sql_query = state["metadata"].get("generated_sql", "")
        retries = state["metadata"].get("sql_failed_times", 0)
        
        try:
            # Mock SQL execution - in real implementation, this would connect to database
            # For now, we'll simulate a successful query
            mock_results = [
                {"id": 1, "name": "Example User", "email": "user@example.com"},
                {"id": 2, "name": "Another User", "email": "another@example.com"}
            ]
            
            state["metadata"]["executed_sql"] = {"status": "success", "data": mock_results}
            state["metadata"]["sql_failed_times"] = retries
            
        except Exception as exc:
            msg = str(exc)
            logger.info("DB error: %s", msg)
            state["metadata"]["executed_sql"] = None
            state["metadata"]["sql_failed_times"] = retries + 1
            state["metadata"]["final_sql_execution_error"] = msg
        
        state["current_step"] = "execute_sql"
        return state
    
    def _sql_executed_edge(self, state: FlowState) -> str:
        """Route based on SQL execution result"""
        if state["metadata"].get("executed_sql") or state["metadata"].get("sql_failed_times", 0) >= 3:
            return "format_final_response"
        return "generate_sql"
    
    def _ask_general_question(self, state: FlowState) -> FlowState:
        """Handle non-SQL user questions"""
        user_message = self.get_last_user_message(state) or ""
        
        general_prompt = f"""
        Answer the following general question:
        
        {user_message}
        
        Provide a helpful and informative response.
        """
        
        response = self.llm.invoke([HumanMessage(content=general_prompt)])
        
        state["metadata"]["final_llm_message"] = str(response.content)
        state["current_step"] = "general_questions"
        
        return state
    
    def _format_final_response(self, state: FlowState) -> FlowState:
        """Assemble final structured response"""
        formatted = {
            "conversation": state["metadata"].get("conversation_id"),
            "Message": state["metadata"].get("final_llm_message"),
            "QueryResults": state["metadata"].get("executed_sql"),
            "ReasoningSteps": state["metadata"].get("reasoning_steps", []),
            "GeneratedSQL": state["metadata"].get("generated_sql"),
            "SQLValid": state["metadata"].get("sql_valid"),
            "Classification": state["metadata"].get("classification")
        }
        
        # Add the response to the conversation
        response_content = state["metadata"].get("final_llm_message", "No response generated")
        state = self.add_message(state, response_content, "assistant")
        
        state["metadata"]["formatted_final_response"] = formatted
        state["current_step"] = "format_final_response"
        
        return state
    
    def get_description(self) -> str:
        return """
        Text-to-SQL Flow:
        
        This flow converts natural language queries into SQL with comprehensive validation.
        
        Process:
        1. Classify the request (general vs SQL)
        2. Rewrite prompt for SQL generation
        3. Identify relevant database tables
        4. Human-in-the-loop table approval
        5. Generate SQL query
        6. Validate SQL correctness
        7. Execute query and format results
        
        Features:
        - Intelligent request classification
        - Table and column identification
        - SQL validation and error correction
        - Human-in-the-loop approval steps
        - Comprehensive error handling
        - Detailed reasoning steps
        """ 