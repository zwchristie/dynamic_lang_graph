import re
import json
import logging
from typing import Dict, Any, List, Optional
try:
    import pandas as pd
except ImportError:
    pd = None
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError

logger = logging.getLogger(__name__)

def extract_sql_from_response(response: Dict[str, Any]) -> str:
    """
    Extract SQL query from LLM response.
    
    Args:
        response: Dictionary containing LLM response with 'Message' key
        
    Returns:
        Extracted SQL query as string
    """
    message = response.get("Message", "")
    if not message:
        return ""
    
    # Try to extract SQL from markdown code blocks
    sql_pattern = r'```sql\s*(.*?)\s*```'
    sql_match = re.search(sql_pattern, message, re.DOTALL | re.IGNORECASE)
    
    if sql_match:
        return sql_match.group(1).strip()
    
    # Try to extract SQL without markdown
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
    lines = message.split('\n')
    sql_lines = []
    
    for line in lines:
        line = line.strip()
        if any(keyword in line.upper() for keyword in sql_keywords):
            sql_lines.append(line)
    
    if sql_lines:
        return ' '.join(sql_lines)
    
    return message.strip()

def generate_query_results(sql_query: str, database_url: Optional[str] = None):
    """
    Execute SQL query and return results as pandas DataFrame.
    
    Args:
        sql_query: SQL query to execute
        database_url: Database connection URL (optional, uses default if not provided)
        
    Returns:
        DataFrame with query results
        
    Raises:
        DatabaseError: If query execution fails
    """
    if pd is None:
        raise ImportError("pandas is required for database operations")
        
    if not database_url:
        # Use default SQLite database for testing
        database_url = "sqlite:///./app.db"
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            
            # Fetch results
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=columns)
            
            return df
            
    except DatabaseError as e:
        logger.error(f"Database error executing query: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error executing query: {e}")
        raise DatabaseError(f"Query execution failed: {str(e)}")

def validate_sql_syntax(sql_query: str) -> Dict[str, Any]:
    """
    Basic SQL syntax validation.
    
    Args:
        sql_query: SQL query to validate
        
    Returns:
        Dictionary with validation results
    """
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Basic syntax checks
    sql_upper = sql_query.upper()
    
    # Check for required SQL keywords
    if not any(keyword in sql_upper for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']):
        validation_result["errors"].append("No valid SQL statement found")
        validation_result["is_valid"] = False
    
    # Check for balanced parentheses
    if sql_query.count('(') != sql_query.count(')'):
        validation_result["errors"].append("Unbalanced parentheses")
        validation_result["is_valid"] = False
    
    # Check for semicolon at end (optional)
    if not sql_query.strip().endswith(';'):
        validation_result["warnings"].append("Missing semicolon at end of statement")
    
    return validation_result

def format_query_results(df, max_rows: int = 10) -> Dict[str, Any]:
    """
    Format query results for API response.
    
    Args:
        df: DataFrame with query results
        max_rows: Maximum number of rows to include in response
        
    Returns:
        Formatted results dictionary
    """
    if df.empty:
        return {
            "status": "success",
            "data": [],
            "row_count": 0,
            "message": "Query returned no results"
        }
    
    # Limit rows for response
    if len(df) > max_rows:
        df_display = df.head(max_rows)
        message = f"Showing first {max_rows} rows of {len(df)} total results"
    else:
        df_display = df
        message = f"Retrieved {len(df)} rows"
    
    # Convert to list of dictionaries
    records = df_display.to_dict(orient='records')
    
    return {
        "status": "success",
        "data": records,
        "row_count": len(df),
        "message": message,
        "columns": list(df.columns)
    } 