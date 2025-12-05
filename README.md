# Multi-Agent Market Research Proposal Generator

An intelligent multi-agent system that automates the market research proposal process from RFP receipt through final PowerPoint delivery.

## Features

- **Multi-Agent Architecture**: 8 specialized agents working together
- **Intelligent Workflow**: Automated coordination with state machine
- **LLM Integration**: Google Gemini + Anthropic Claude with smart provider selection
- **Vector Search**: PostgreSQL with pgvector for semantic search
- **Async Processing**: Celery + Redis for scalable task execution
- **Email Automation**: SMTP/IMAP with thread management and deduplication
- **Notion Integration**: Real-time workspace visibility
- **PowerPoint Generation**: Claude-powered presentation creation
- **Comprehensive Monitoring**: Prometheus metrics, structured logging, health checks
- **Knowledge Base**: Continuous learning and capability tracking

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL with pgvector extension
- Redis
- API keys for Google Gemini, Anthropic Claude

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd proposal_bot
```

2. Run setup script:
```bash
python setup.py
```

3. Edit the .env file with your API keys and configuration

4. Set up the database:
```bash
# Create PostgreSQL database
createdb proposal_bot

# Enable pgvector extension
psql proposal_bot -c "CREATE EXTENSION vector;"
```

5. Start the services:

   **Terminal 1 - Main API:**
   ```bash
   python main.py
   ```

   **Terminal 2 - Celery Worker:**
   ```bash
   celery -A app.core.celery_app worker --loglevel=info --concurrency=4
   ```

   **Terminal 3 - Celery Beat Scheduler:**
   ```bash
   celery -A app.core.celery_app beat --loglevel=info
   ```

The API will be available at `http://localhost:8000`

## Implemented Agents

### 🤖 **Orchestrator Agent**
- Central coordinator managing workflow state
- Intelligent decision making using Claude
- State machine with 10 workflow statuses
- Timeout handling and escalation

### 📧 **Email Agent**
- SMTP/IMAP integration for all communications
- Thread management with Redis tracking
- 48-hour deduplication protection
- Validation requests and client clarifications

### 📋 **Brief Review Agent**
- Comprehensive RFP analysis using Claude
- Requirements extraction and ambiguity detection
- Go/no-go scoring based on firm capabilities
- Project lead recommendations

### 📅 **Planning Agent**
- Resource discovery and semantic matching
- Validation orchestration with concurrent emails
- Timeline and cost estimation
- Design questions for complex decisions

### 💼 **Go to Market Agent**
- Professional proposal outlining
- Pricing logic with markup rules and contingencies
- Quality assurance against requirements
- Client-ready business language

### 🧠 **Knowledge Agent**
- Continuous learning from validations
- Confidence score updates
- Pattern recognition and inference rules
- High-impact change flagging

### 📝 **Notion Agent**
- Real-time project tracking pages
- Activity feed and status updates
- Resource calendar management
- User feedback relay to agents

### 📊 **PowerPoint Agent**
- Claude-powered presentation generation
- Professional templates and branding
- Asset library integration
- Revision management with feedback

## API Endpoints

### Core Functionality
- `POST /rfp/submit` - Submit a new RFP for processing
- `GET /project/{project_id}` - Get project status and details
- `GET /projects` - List all projects with pagination

### Monitoring & Health
- `GET /health` - Basic health check
- `GET /health/detailed` - Comprehensive system health check
- `GET /metrics` - Prometheus metrics endpoint
- `GET /status` - System status overview
- `GET /docs` - Interactive API documentation

## Architecture

### Agents

- **Orchestrator Agent**: Central coordinator managing workflow state
- **Email Agent**: Handles all email communication
- **Brief Review Agent**: Analyzes incoming RFPs and extracts requirements
- **Planning Agent**: Matches requirements to available resources
- **Go to Market Agent**: Creates client-ready proposals with pricing
- **Knowledge Agent**: Maintains knowledge base accuracy
- **Notion Agent**: Provides visibility via Notion workspace
- **PowerPoint Agent**: Generates professional presentations

### Database Schema

- **Resources**: People, vendors, tools, services with capabilities
- **Documents**: Proposals, resumes, case studies with vector embeddings
- **Projects**: Workflow state and project management
- **Validations**: Resource validation tracking

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Database Migrations

```bash
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```

## Configuration

See `env.template` for all available configuration options. Key settings include:

- Database connection strings
- LLM API keys
- Email server configuration
- Notion integration tokens
- Timeout and concurrency settings

## Deployment

The application can be deployed to:

- Railway
- Fly.io
- Render
- Any container platform

Use the included `Dockerfile` for containerized deployment.

## Monitoring & Observability

### Metrics
- **Prometheus Integration**: `/metrics` endpoint exposes 15+ metrics
- **Agent Performance**: Execution counts, latency, success rates
- **Project Pipeline**: Status distribution, transition counts
- **LLM Usage**: API calls, token consumption, costs by provider
- **Email Automation**: Send/receive rates, thread tracking
- **System Health**: Queue lengths, connection status

### Logging
- **Structured JSON**: Production-ready log format
- **Agent Actions**: All agent decisions and reasoning logged
- **Performance Tracking**: Slow operations automatically flagged
- **Error Context**: Comprehensive error information with stack traces

### Health Checks
- **Multi-level Checks**: Basic, detailed, and component-specific
- **Dependency Monitoring**: Database, Redis, LLM providers, email
- **Automated Alerts**: Configurable thresholds and notifications

## License

[Add your license here]