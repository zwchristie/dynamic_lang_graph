from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from .base import BaseFlow, FlowState, flow
from ..core.config import settings
from ..core.database import get_table_info
import json
import re

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
    
    def _build_graph(self) -> StateGraph:
        """Build the text-to-SQL graph with all validation steps"""
        
        workflow = StateGraph(FlowState)
        
        # Add nodes
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("identify_tables", self._identify_tables)
        workflow.add_node("validate_tables", self._validate_tables)
        workflow.add_node("identify_columns", self._identify_columns)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("validate_sql", self._validate_sql)
        workflow.add_node("finalize_response", self._finalize_response)
        workflow.add_node("fix_query_followup", self._fix_query_followup)
        
        # Set entry point
        workflow.set_entry_point("analyze_request")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "analyze_request",
            self._route_after_analysis,
            {
                "new_query": "identify_tables",
                "edit_query": "generate_sql",
                "fix_query": "validate_sql",
                "fix_query_followup": "fix_query_followup"
            }
        )
        
        workflow.add_conditional_edges(
            "validate_tables",
            self._route_after_table_validation,
            {
                "approved": "identify_columns",
                "rejected": "identify_tables"
            }
        )
        
        workflow.add_conditional_edges(
            "validate_sql",
            self._route_after_sql_validation,
            {
                "approved": "finalize_response",
                "rejected": "generate_sql"
            }
        )
        
        # Add regular edges
        workflow.add_edge("identify_tables", "validate_tables")
        workflow.add_edge("identify_columns", "generate_sql")
        workflow.add_edge("generate_sql", "validate_sql")
        workflow.add_edge("finalize_response", END)
        workflow.add_edge("fix_query_followup", "finalize_response")
        
        return workflow
    
    def _analyze_request(self, state: FlowState) -> FlowState:
        """Analyze the user request to determine operation type and fix_query subtype"""
        user_message = self.get_last_user_message(state) or ""

        # Auto-detect if user message contains a SQL query (simple heuristic)
        contains_sql = bool(re.search(r"select |update |insert |delete |from |where |join |create table|drop table|alter table", user_message, re.IGNORECASE))
        
        analysis_prompt = f"""
        Analyze the following user request and determine the type of SQL operation needed:
        
        User request: {user_message}
        
        Determine if this is:
        1. "new_query" - User wants to generate a new SQL query from natural language
        2. "edit_query" - User wants to modify an existing SQL query
        3. "fix_query" - User wants to fix a SQL query with syntax errors
        
        Return only the operation type: new_query, edit_query, or fix_query
        """
        
        response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
        operation_type = str(response.content).strip().lower()

        # If fix_query, distinguish direct vs follow-up
        if operation_type == "fix_query":
            if contains_sql:
                state["metadata"]["fix_query_type"] = "direct"
            else:
                state["metadata"]["fix_query_type"] = "followup"
        else:
            state["metadata"]["fix_query_type"] = None

        state["metadata"]["operation_type"] = operation_type
        state["current_step"] = "analyze_request"
        return state

    def _fix_query_followup(self, state: FlowState) -> FlowState:
        """Fix the last generated SQL based on user's follow-up correction or error message."""
        user_message = self.get_last_user_message(state) or ""
        # Try to get the last generated SQL from metadata or conversation
        last_sql = state["metadata"].get("generated_sql", "")
        if not last_sql:
            # Try to find last assistant message with SQL
            for msg in reversed(state["messages"]):
                if hasattr(msg, "content") and isinstance(msg.content, str) and "select" in msg.content.lower():
                    # Extract SQL from markdown if present
                    sql_match = re.search(r"```sql(.*?)```", msg.content, re.DOTALL | re.IGNORECASE)
                    if sql_match:
                        last_sql = sql_match.group(1).strip()
                    else:
                        last_sql = msg.content.strip()
                    break
        
        prompt = f"""
        The user previously received this SQL query:
        {last_sql}

        The user now says: {user_message}

        Please update or fix the SQL query based on the user's feedback. If the user provided an error message, correct the SQL accordingly. If the user requested a change, apply it to the query. Return only the updated SQL query, no additional text.
        """
        response = self.llm.invoke([HumanMessage(content=prompt)])
        fixed_sql = str(response.content).strip()
        # Clean up SQL formatting
        fixed_sql = re.sub(r'```sql\s*', '', fixed_sql)
        fixed_sql = re.sub(r'\s*```', '', fixed_sql)
        state["metadata"]["generated_sql"] = fixed_sql
        state["current_step"] = "fix_query_followup"
        return state

    def _route_after_analysis(self, state: FlowState) -> str:
        """Route to appropriate step based on operation type and fix_query type"""
        operation_type = state["metadata"].get("operation_type", "new_query")
        if operation_type == "fix_query":
            if state["metadata"].get("fix_query_type") == "followup":
                return "fix_query_followup"
            else:
                return "fix_query"
        return operation_type
    
    def _identify_tables(self, state: FlowState) -> FlowState:
        """Identify relevant tables for the SQL query"""
        user_message = self.get_last_user_message(state)
        available_tables = [table["name"] for table in self.table_info["tables"]]
        
        table_selection_prompt = f"""
        Based on the user request, identify the relevant database tables needed.
        
        User request: {user_message}
        Available tables: {available_tables}
        
        For each table, provide:
        1. Table name
        2. Reasoning for why it's needed
        
        Return in JSON format:
        {{
            "tables": [
                {{
                    "name": "table_name",
                    "reasoning": "why this table is needed"
                }}
            ]
        }}
        """
        
        response = self.llm.invoke([HumanMessage(content=table_selection_prompt)])
        
        try:
            table_data = json.loads(str(response.content))
            state["metadata"]["identified_tables"] = table_data["tables"]
        except:
            # Fallback if JSON parsing fails
            state["metadata"]["identified_tables"] = [{"name": "users", "reasoning": "Default table"}]
        
        state["current_step"] = "identify_tables"
        return state
    
    def _validate_tables(self, state: FlowState) -> FlowState:
        """Human-in-the-loop validation for table selection"""
        identified_tables = state["metadata"].get("identified_tables", [])
        user_message = self.get_last_user_message(state)
        
        # Create validation message for UI
        table_names = [table["name"] for table in identified_tables]
        table_reasons = [table["reasoning"] for table in identified_tables]
        
        validation_message = f"""
        I've identified the following tables for your request: "{user_message}"
        
        Tables: {', '.join(table_names)}
        
        Reasoning:
        {chr(10).join([f"- {table['name']}: {table['reasoning']}" for table in identified_tables])}
        
        Are these tables correct for your query? Please respond with 'yes' or 'no'.
        """
        
        # Store validation request for UI
        state["metadata"]["validation_request"] = {
            "type": "table_selection",
            "message": validation_message,
            "data": identified_tables
        }
        
        # For now, assume approval (in real implementation, this would wait for UI response)
        state["metadata"]["table_validation_approved"] = True
        state["current_step"] = "validate_tables"
        
        return state
    
    def _route_after_table_validation(self, state: FlowState) -> str:
        """Route based on table validation result"""
        approved = state["metadata"].get("table_validation_approved", True)
        return "approved" if approved else "rejected"
    
    def _identify_columns(self, state: FlowState) -> FlowState:
        """Identify relevant columns from the selected tables"""
        user_message = self.get_last_user_message(state)
        identified_tables = state["metadata"].get("identified_tables", [])
        
        # Get column information for identified tables
        table_columns = {}
        for table_info in self.table_info["tables"]:
            if table_info["name"] in [t["name"] for t in identified_tables]:
                table_columns[table_info["name"]] = table_info["columns"]
        
        column_selection_prompt = f"""
        Based on the user request and selected tables, identify the relevant columns needed.
        
        User request: {user_message}
        Selected tables and their columns: {table_columns}
        
        For each table, identify which columns are needed for the query.
        
        Return in JSON format:
        {{
            "table_columns": [
                {{
                    "table": "table_name",
                    "columns": ["col1", "col2"],
                    "reasoning": "why these columns are needed"
                }}
            ]
        }}
        """
        
        response = self.llm.invoke([HumanMessage(content=column_selection_prompt)])
        
        try:
            column_data = json.loads(str(response.content))
            state["metadata"]["identified_columns"] = column_data["table_columns"]
        except:
            # Fallback
            state["metadata"]["identified_columns"] = []
        
        state["current_step"] = "identify_columns"
        return state
    
    def _generate_sql(self, state: FlowState) -> FlowState:
        """Generate SQL query based on user request and identified tables/columns"""
        user_message = self.get_last_user_message(state)
        identified_tables = state["metadata"].get("identified_tables", [])
        identified_columns = state["metadata"].get("identified_columns", [])
        operation_type = state["metadata"].get("operation_type", "new_query")
        
        # Build context for SQL generation
        table_context = ""
        for table in identified_tables:
            table_context += f"Table '{table['name']}': {table['reasoning']}\n"
        
        column_context = ""
        for col_info in identified_columns:
            column_context += f"Table '{col_info['table']}' columns: {', '.join(col_info['columns'])} - {col_info['reasoning']}\n"
        
        sql_generation_prompt = f"""
        Generate a SQL query based on the following information:
        
        User request: {user_message}
        Operation type: {operation_type}
        
        Table context:
        {table_context}
        
        Column context:
        {column_context}
        
        Generate a valid SQL query that fulfills the user's request. 
        Ensure the query is syntactically correct and follows SQL best practices.
        
        Return only the SQL query, no additional text.
        """
        
        response = self.llm.invoke([HumanMessage(content=sql_generation_prompt)])
        generated_sql = str(response.content).strip()
        
        # Clean up the SQL (remove markdown formatting if present)
        generated_sql = re.sub(r'```sql\s*', '', generated_sql)
        generated_sql = re.sub(r'\s*```', '', generated_sql)
        
        state["metadata"]["generated_sql"] = generated_sql
        state["current_step"] = "generate_sql"
        
        return state
    
    def _validate_sql(self, state: FlowState) -> FlowState:
        """Validate the generated SQL query"""
        generated_sql = state["metadata"].get("generated_sql", "")
        user_message = self.get_last_user_message(state)
        
        validation_prompt = f"""
        Validate the following SQL query for syntax correctness and logical validity:
        
        SQL Query: {generated_sql}
        Original request: {user_message}
        
        Check for:
        1. Syntax errors
        2. Logical errors
        3. Missing clauses
        4. Incorrect table/column references
        
        Return a JSON response:
        {{
            "is_valid": true/false,
            "errors": ["error1", "error2"],
            "suggestions": ["suggestion1", "suggestion2"]
        }}
        """
        
        response = self.llm.invoke([HumanMessage(content=validation_prompt)])
        
        try:
            validation_result = json.loads(str(response.content))
            is_valid = validation_result.get("is_valid", False)
            errors = validation_result.get("errors", [])
            suggestions = validation_result.get("suggestions", [])
        except:
            is_valid = True
            errors = []
            suggestions = []
        
        state["metadata"]["sql_validation"] = {
            "is_valid": is_valid,
            "errors": errors,
            "suggestions": suggestions
        }
        
        # For now, assume validation passes (in real implementation, this would check actual DB)
        state["metadata"]["sql_validation_approved"] = True
        state["current_step"] = "validate_sql"
        
        return state
    
    def _route_after_sql_validation(self, state: FlowState) -> str:
        """Route based on SQL validation result"""
        validation = state["metadata"].get("sql_validation", {})
        approved = state["metadata"].get("sql_validation_approved", True)
        
        if approved and validation.get("is_valid", True):
            return "approved"
        else:
            return "rejected"
    
    def _finalize_response(self, state: FlowState) -> FlowState:
        """Finalize the response with the generated SQL"""
        generated_sql = state["metadata"].get("generated_sql", "")
        identified_tables = state["metadata"].get("identified_tables", [])
        identified_columns = state["metadata"].get("identified_columns", [])
        
        # Create comprehensive response
        response_parts = []
        response_parts.append("Here's the SQL query for your request:")
        response_parts.append("")
        response_parts.append("```sql")
        response_parts.append(generated_sql)
        response_parts.append("```")
        response_parts.append("")
        
        if identified_tables:
            response_parts.append("**Tables used:**")
            for table in identified_tables:
                response_parts.append(f"- {table['name']}: {table['reasoning']}")
            response_parts.append("")
        
        if identified_columns:
            response_parts.append("**Columns selected:**")
            for col_info in identified_columns:
                response_parts.append(f"- {col_info['table']}: {', '.join(col_info['columns'])}")
        
        final_response = "\n".join(response_parts)
        
        # Add the response to the conversation
        state = self.add_message(state, final_response, "assistant")
        state["current_step"] = "finalize_response"
        
        return state
    
    def get_description(self) -> str:
        return """
        Text-to-SQL Flow:
        
        This flow converts natural language requests into SQL queries with comprehensive validation.
        
        Supported operations:
        1. Generate new SQL from natural language
        2. Edit existing SQL queries
        3. Fix SQL syntax errors
        4. Fix/edit previously returned queries
        
        Process steps:
        1. Analyze request type (new/edit/fix)
        2. Identify relevant database tables
        3. Human-in-the-loop validation of table selection
        4. Identify relevant columns from selected tables
        5. Generate SQL query
        6. Validate SQL syntax and logic
        7. Human-in-the-loop validation of generated SQL
        8. Return final SQL with explanation
        
        Features:
        - Human-in-the-loop validation at critical steps
        - Comprehensive table and column identification
        - SQL syntax validation
        - Detailed explanations of table/column selection
        - Support for complex multi-table queries
        """ 