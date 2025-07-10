"""
Prompt generation functions for the text-to-SQL flow.
These functions create the prompts used by the LLM for various tasks.
"""

def identify_product_and_tables_prompt(user_query: str, schema_info: str) -> str:
    """Generate prompt for identifying relevant tables"""
    return f"""
    Based on the user query, identify the relevant database tables and their purpose.
    
    User Query: {user_query}
    Available Schema: {schema_info}
    
    Return in JSON format:
    {{
        "tables": ["table1", "table2"],
        "reasoning": "Why these tables are needed"
    }}
    """

def generate_sql_prompt(user_query: str, schema_info: str) -> str:
    """Generate prompt for SQL generation"""
    return f"""
    Generate a SQL query based on the user request.
    
    User Request: {user_query}
    Available Schema: {schema_info}
    
    Return only the SQL query, no additional text or explanations.
    """

def fix_sql_prompt(user_query: str, schema_info: str, error_message: str = "", 
                   empty_return: bool = False, previous_sql: str = "") -> str:
    """Generate prompt for fixing SQL errors"""
    context = ""
    if error_message:
        context += f"Error: {error_message}\n"
    if empty_return:
        context += "Previous query returned no results.\n"
    if previous_sql:
        context += f"Previous SQL: {previous_sql}\n"
    
    return f"""
    Fix the SQL query based on the error or user feedback.
    
    User Request: {user_query}
    Available Schema: {schema_info}
    {context}
    
    Return only the corrected SQL query, no additional text.
    """

def generate_extend_user_prompt(user_query: str, system_prompt: str) -> str:
    """Generate prompt for extending user query with system context"""
    return f"""
    {system_prompt}
    
    Original user request: {user_query}
    
    Please rewrite this request to be more specific for SQL generation, 
    including any clarifying details that would help generate accurate SQL.
    """

def filter_relevant_tables_prompt(user_query: str, schema_info: str) -> str:
    """Generate prompt for filtering relevant columns"""
    return f"""
    Based on the user request, identify only the relevant columns from the schema.
    
    User Request: {user_query}
    Available Schema: {schema_info}
    
    Return only the relevant columns in JSON format:
    {{
        "table_name": ["column1", "column2"]
    }}
    """

def validate_llm_sql(user_query: str, sql_query: str, schema_info: str) -> str:
    """Generate prompt for SQL validation"""
    return f"""
    Validate the SQL query for correctness and relevance to the user request.
    
    User Request: {user_query}
    Generated SQL: {sql_query}
    Available Schema: {schema_info}
    
    Check for:
    1. Syntax correctness
    2. Relevance to user request
    3. Proper table and column usage
    
    Return only: VALID or INVALID
    """ 