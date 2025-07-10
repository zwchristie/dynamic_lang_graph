import json
import logging
from typing import Dict, Any, List, Optional
from ..core.database import get_table_info

logger = logging.getLogger(__name__)

class MetadataManager:
    """Manages database metadata and schema information"""
    
    def __init__(self):
        self.table_info = get_table_info()
        self._schema_cache = {}
    
    def get_concise_schema(self) -> str:
        """Get a concise representation of the database schema"""
        if not self.table_info or "tables" not in self.table_info:
            return "{}"
        
        concise_schema = {}
        for table in self.table_info["tables"]:
            table_name = table.get("name", "")
            columns = [col.get("name", "") for col in table.get("columns", [])]
            concise_schema[table_name] = columns
        
        return json.dumps(concise_schema, indent=2)
    
    def get_relevant_schema_text(self, table_names: List[str]) -> str:
        """Get detailed schema information for specific tables"""
        if not table_names:
            return ""
        
        schema_info = {}
        for table_name in table_names:
            for table in self.table_info.get("tables", []):
                if table.get("name") == table_name:
                    columns = []
                    for col in table.get("columns", []):
                        col_info = {
                            "name": col.get("name", ""),
                            "type": col.get("type", ""),
                            "nullable": col.get("nullable", True)
                        }
                        columns.append(col_info)
                    
                    schema_info[table_name] = {
                        "columns": columns,
                        "description": table.get("description", "")
                    }
                    break
        
        return json.dumps(schema_info, indent=2)
    
    def get_table_names(self) -> List[str]:
        """Get list of all table names"""
        return [table.get("name", "") for table in self.table_info.get("tables", [])]
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a specific table"""
        for table in self.table_info.get("tables", []):
            if table.get("name") == table_name:
                return table.get("columns", [])
        return []
    
    def validate_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the schema"""
        return table_name in self.get_table_names()
    
    def get_table_relationships(self, table_name: str) -> List[Dict[str, Any]]:
        """Get relationship information for a table"""
        # This would be implemented based on your specific schema format
        # For now, return empty list
        return [] 