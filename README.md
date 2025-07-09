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

## Environment Setup

The application supports three environments: **local**, **dev**, and **testing**. Each environment has its own configuration file and SSL certificate requirements.

### Environment Files

- `env.local` - Local development (no SSL required)
- `env.dev` - Development environment (SSL required)
- `env.testing` - Testing environment (SSL required)

### Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your environment files:
```bash
# Copy and edit environment files
cp env.example env.local
cp env.example env.dev
cp env.example env.testing
```

3. Generate SSL certificates (for dev/testing environments):
```bash
python generate_certs.py
```

4. Run the application:

**Local environment (no SSL):**
```bash
python run.py local
```

**Development environment (with SSL):**
```bash
python run.py dev
```

**Testing environment (with SSL):**
```bash
python run.py testing
```

### Manual Setup

If you prefer to run manually:

**Local:**
```bash
ENVIRONMENT=local python -m app.main
```

**Development:**
```bash
ENVIRONMENT=dev python -m app.main
```

**Testing:**
```bash
ENVIRONMENT=testing python -m app.main
```

### Certificate Management

For development and testing environments, self-signed certificates are used. The `generate_certs.py` script creates:

- `./certs/dev_cert.pem` - Development certificate
- `./certs/dev_key.pem` - Development private key
- `./certs/test_cert.pem` - Testing certificate
- `./certs/test_key.pem` - Testing private key

**Note:** Self-signed certificates will show browser security warnings - this is expected for development environments.

### Environment Configuration

Each environment file (`env.local`, `env.dev`, `env.testing`) contains:

```bash
# Environment selection
ENVIRONMENT=local|dev|testing

# Provider settings
PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4

# Server settings
HOST=127.0.0.1|0.0.0.0
PORT=8000|8443|8444

# SSL settings (for dev/testing)
SSL_CERT_FILE=./certs/dev_cert.pem
SSL_KEY_FILE=./certs/dev_key.pem

# Database settings
DATABASE_URL=sqlite:///./app.db

# App settings
APP_NAME=Agentic Workflow System
DEBUG=True|False
MAX_ITERATIONS=10
```

### Port Configuration

- **Local**: Port 8000 (HTTP)
- **Development**: Port 8443 (HTTPS)
- **Testing**: Port 8444 (HTTPS)

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