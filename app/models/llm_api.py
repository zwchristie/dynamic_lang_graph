"""
LLM API models and utilities for parsing responses.
"""

import json
import re
from typing import Dict, Any, Optional

def parse_json_from_response(response_text: str) -> Dict[str, Any]:
    """
    Parse JSON from LLM response text.
    
    Args:
        response_text: Raw response text from LLM
        
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        ValueError: If JSON parsing fails
    """
    if not response_text:
        return {}
    
    # Try to extract JSON from markdown code blocks
    json_pattern = r'```json\s*(.*?)\s*```'
    json_match = re.search(json_pattern, response_text, re.DOTALL | re.IGNORECASE)
    
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON in the text
    try:
        # Look for JSON-like structure
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx + 1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # If no JSON found, try to parse as simple key-value pairs
    try:
        # Simple parsing for basic structures
        lines = response_text.strip().split('\n')
        result = {}
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().strip('"{}')
                value = value.strip().strip('"{}')
                if key and value:
                    result[key] = value
        
        return result
    except:
        pass
    
    # Return empty dict if all parsing attempts fail
    return {}

def extract_sql_from_response(response: Dict[str, Any]) -> str:
    """
    Extract SQL query from LLM response.
    
    Args:
        response: Dictionary containing LLM response
        
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

def validate_json_response(response_text: str) -> bool:
    """
    Validate if response contains valid JSON.
    
    Args:
        response_text: Raw response text
        
    Returns:
        True if valid JSON found, False otherwise
    """
    try:
        parse_json_from_response(response_text)
        return True
    except:
        return False

def extract_error_from_response(response: Dict[str, Any]) -> Optional[str]:
    """
    Extract error message from LLM response.
    
    Args:
        response: Dictionary containing LLM response
        
    Returns:
        Error message if found, None otherwise
    """
    message = response.get("Message", "")
    
    # Look for error indicators
    error_indicators = ["error", "failed", "invalid", "incorrect", "syntax error"]
    
    for indicator in error_indicators:
        if indicator.lower() in message.lower():
            # Extract the sentence containing the error
            sentences = message.split('.')
            for sentence in sentences:
                if indicator.lower() in sentence.lower():
                    return sentence.strip()
    
    return None 