
def get_table_info():
    """Get information about available tables"""
    # This would be implemented based on your specific database schema
    # For now, returning a placeholder structure
    return {
        "tables": [
            {
                "name": "users",
                "columns": ["id", "name", "email", "created_at"],
                "description": "User information table"
            },
            {
                "name": "orders", 
                "columns": ["id", "user_id", "product_id", "quantity", "total", "created_at"],
                "description": "Order information table"
            }
        ]
    } 

class SchemaDocumentParser:
    @staticmethod
    def parse_schema_json(schema_json: dict) -> list[str]:
        """
        Parse a schema JSON document into readable text chunks for embedding.
        Each chunk describes a table, its columns, and relationships.
        """
        chunks = []
        catalog = schema_json.get("catalog", "")
        schema = schema_json.get("schema", "")
        models = schema_json.get("models", [])
        relationships = schema_json.get("relationships", [])

        # Build a lookup for relationships
        rel_lookup = {}
        for rel in relationships:
            for model in rel.get("models", []):
                rel_lookup.setdefault(model, []).append(rel)

        for model in models:
            table_name = model.get("name", "")
            table_ref = model.get("tableReference", {})
            columns = model.get("columns", [])
            primary_key = model.get("primaryKey", "")

            # Table header
            table_header = f"Table: {table_name}\nCatalog: {table_ref.get('catalog', catalog)}, Schema: {table_ref.get('schema', schema)}, Table: {table_ref.get('table', table_name)}"
            # Columns
            col_lines = []
            for col in columns:
                col_desc = f"- {col.get('name', '')}: {col.get('type', '')}"
                if 'expression' in col:
                    col_desc += f" (expr: {col['expression']})"
                if 'relationship' in col:
                    col_desc += f" [rel: {col['relationship']}, type: {col.get('type', '')}]"
                col_lines.append(col_desc)
            # Primary key
            pk_line = f"Primary Key: {primary_key}" if primary_key else ""
            # Relationships
            rel_lines = []
            for rel in rel_lookup.get(table_name, []):
                rel_lines.append(f"Relationship: {rel['name']} ({rel['joinType']}) between {', '.join(rel['models'])} on {rel['condition']}")
            # Combine
            chunk = "\n".join(
                [table_header] + col_lines + ([pk_line] if pk_line else []) + rel_lines
            )
            chunks.append(chunk)
        return chunks 