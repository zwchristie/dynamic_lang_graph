# Agentic Workflow System

A dynamic agentic workflow system built with LangGraph and FastAPI that supports general question answering and text-to-SQL functionality.

## Features

- **Dynamic Flow Generation**: LLM orchestrator dynamically generates workflows based on available flows
- **Modular Flow System**: Each functionality is implemented as a separate "flow" with annotations
- **Text-to-SQL Support**: 
  - Generate new SQL from user query
  - Edit existing SQL
  - Fix SQL syntax errors
  - Fix/edit previously returned queries
- **Human-in-the-Loop**: Interactive validation steps for table selection and query validation

## Project Structure

```
langgraph_project/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration settings
│   │   └── database.py        # Database connection
│   ├── flows/
│   │   ├── __init__.py
│   │   ├── base.py            # Base flow class and decorators
│   │   ├── general_qa.py      # General question answering flow
│   │   └── text_to_sql.py     # Text-to-SQL flow
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   └── services/
│       ├── __init__.py
│       ├── orchestrator.py    # LLM orchestrator service
│       └── flow_registry.py   # Flow registration and discovery
├── requirements.txt
└── .env.example
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file from `.env.example` and configure your OpenAI API key:
```bash
cp .env.example .env
```

3. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `POST /api/chat`: Main chat endpoint for agentic workflows
- `POST /api/flows/register`: Register a new flow
- `GET /api/flows`: List all available flows
- `POST /api/validate`: Human-in-the-loop validation endpoint

## Flow System

Each flow is defined with the `@flow` decorator that automatically registers it with the system:

```python
@flow(name="text_to_sql", description="Convert natural language to SQL queries")
class TextToSQLFlow(BaseFlow):
    # Flow implementation
```

The orchestrator automatically discovers all registered flows and includes them in the LLM context for dynamic workflow generation. 