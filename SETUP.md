# Proposal Automation System - Setup Guide

## Overview

This is a Phase 1 MVP of an automated proposal generation system for the market research industry. It uses AI (Claude/GPT) to extract requirements from RFPs and generate professional proposals.

## Architecture

### Backend (FastAPI + PostgreSQL)
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ with pgvector extension
- **LLM**: Anthropic Claude (primary) + OpenAI GPT (fallback)
- **Storage**: MinIO (local) or AWS S3 (production)

### Key Features
- ✅ RFP submission (text or file upload)
- ✅ AI-powered requirement extraction
- ✅ Semantic capability matching with vector search
- ✅ Automated proposal generation
- ✅ Human review and editing workflow
- ✅ AI-powered proposal revision based on feedback
- ✅ PDF generation
- ✅ Status tracking (draft/review/approved/sent/won/lost)

## Prerequisites

1. **Docker & Docker Compose** (recommended)
   - Docker Desktop 4.0+ or Docker Engine 20.10+
   - Docker Compose 2.0+

2. **OR Manual Setup:**
   - Python 3.11+
   - PostgreSQL 15+ with pgvector extension
   - Node.js 18+ (for future frontend)

3. **API Keys** (required):
   - Anthropic API key (primary LLM)
   - OpenAI API key (fallback LLM + embeddings)

## Quick Start with Docker (Recommended)

### 1. Clone and Setup

```bash
cd Proposal_bot
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` and add your API keys:

```bash
# Required: Add your API keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here

# Optional: Customize other settings
POSTGRES_PASSWORD=your-secure-password
JWT_SECRET_KEY=your-secret-key-for-jwt
```

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (with pgvector) on port 5432
- MinIO (object storage) on ports 9000 & 9001
- Backend API on port 8000

### 4. Initialize Database

Wait for services to be healthy (about 30 seconds), then:

```bash
docker-compose exec backend python init_db.py
```

You should see:
```
✅ Database initialized successfully!
📧 Admin login: admin@example.com
🔑 Password: admin123
```

### 5. Verify Installation

Check health:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development",
  "timestamp": "2024-12-04T..."
}
```

## API Documentation

Once running, access interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Manual Setup (Without Docker)

### 1. Install PostgreSQL with pgvector

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-15 postgresql-15-pgvector

# macOS (Homebrew)
brew install postgresql@15
brew install pgvector

# Start PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql@15  # macOS
```

### 2. Create Database

```bash
sudo -u postgres psql

CREATE DATABASE proposal_automation;
CREATE USER proposal_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE proposal_automation TO proposal_user;

\c proposal_automation
CREATE EXTENSION vector;
\q
```

### 3. Setup Backend

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example ../.env
# Edit .env with your settings

# Initialize database
python init_db.py

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Usage Examples

### 1. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin123"
  }'
```

Save the `access_token` from the response.

### 2. Submit RFP (Text)

```bash
curl -X POST http://localhost:8000/api/v1/rfp/submit \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "client_name=Acme Corp" \
  -F "client_email=buyer@acme.com" \
  -F "raw_content=We are seeking proposals for a customer satisfaction survey. Target: 500 customers in the US. Timeline: Feb-Apr 2025. Budget: $50,000. Deliverables: Executive report and raw data."
```

### 3. Get RFP with Extracted Requirements

```bash
curl -X GET http://localhost:8000/api/v1/rfp/{rfp_id} \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Generate Proposal

```bash
curl -X POST http://localhost:8000/api/v1/proposals/generate \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rfp_id": "YOUR_RFP_ID"}'
```

### 5. Get Generated Proposal

```bash
curl -X GET http://localhost:8000/api/v1/proposals/{proposal_id} \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Request Revision with Feedback

```bash
curl -X POST http://localhost:8000/api/v1/proposals/{proposal_id}/regenerate \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"feedback": "Reduce total price by 10% and emphasize focus group expertise more"}'
```

### 7. Generate PDF

```bash
curl -X POST http://localhost:8000/api/v1/proposals/{proposal_id}/generate-pdf \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Project Structure

```
Proposal_bot/
├── backend/
│   ├── alembic/              # Database migrations
│   ├── api/                  # API endpoints
│   │   ├── auth.py          # Authentication
│   │   ├── rfp.py           # RFP operations
│   │   ├── proposals.py     # Proposal operations
│   │   ├── capabilities.py  # Capability management
│   │   └── resources.py     # Resource management
│   ├── models/               # Data models
│   │   ├── database.py      # Database connection
│   │   ├── orm.py           # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── services/             # Business logic
│   │   ├── llm_service.py   # LLM integration
│   │   ├── extraction_service.py
│   │   ├── proposal_service.py
│   │   ├── pdf_service.py
│   │   └── prompts.py       # LLM prompts
│   ├── utils/                # Utilities
│   │   ├── auth.py          # JWT handling
│   │   └── file_storage.py  # S3/MinIO
│   ├── config.py             # Configuration
│   ├── main.py               # FastAPI app
│   ├── init_db.py            # Database initialization
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── SETUP.md (this file)
```

## Key Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login and get JWT token

### RFP Operations
- `POST /api/v1/rfp/submit` - Submit new RFP
- `GET /api/v1/rfp/{id}` - Get RFP details
- `GET /api/v1/rfp/list` - List all RFPs

### Proposal Operations
- `POST /api/v1/proposals/generate` - Generate proposal from RFP
- `GET /api/v1/proposals/{id}` - Get proposal details
- `PATCH /api/v1/proposals/{id}` - Update proposal
- `POST /api/v1/proposals/{id}/regenerate` - Regenerate with feedback
- `POST /api/v1/proposals/{id}/generate-pdf` - Generate PDF
- `GET /api/v1/proposals/list` - List all proposals

### Capability Management
- `GET /api/v1/capabilities/search` - Search capabilities
- `POST /api/v1/capabilities` - Add capability (admin)
- `GET /api/v1/capabilities/{id}` - Get capability

### Resource Management
- `GET /api/v1/resources` - List resources
- `POST /api/v1/resources` - Add resource (admin)
- `GET /api/v1/resources/{id}` - Get resource

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@localhost:5432/proposal_automation` |
| `ANTHROPIC_API_KEY` | Anthropic API key (required) | - |
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `JWT_SECRET_KEY` | Secret for JWT signing | `your-secret-key-change-in-production` |
| `USE_MINIO` | Use MinIO instead of S3 | `true` |
| `DEFAULT_LLM_PROVIDER` | Primary LLM provider | `anthropic` |
| `ENVIRONMENT` | Environment (development/production) | `development` |

## Troubleshooting

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### API Errors

```bash
# View backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Storage Issues

```bash
# Check MinIO is running
docker-compose ps minio

# Access MinIO console
# Open http://localhost:9001
# Login: minioadmin / minioadmin
```

### LLM API Errors

- Verify your API keys are set correctly in `.env`
- Check API key quotas and rate limits
- Review backend logs for detailed error messages

## Next Steps

### Adding Capabilities

```bash
curl -X POST http://localhost:8000/api/v1/capabilities \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "methodology",
    "name": "Online Communities",
    "description": "Long-term online community research...",
    "detailed_description": "Full description for proposals...",
    "typical_duration_weeks": 8,
    "typical_cost_range": {"min": 30000, "max": 80000, "currency": "USD"},
    "complexity_level": "complex",
    "tags": ["qualitative", "longitudinal", "community"]
  }'
```

### Adding Resources

```bash
curl -X POST http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "internal",
    "name": "John Doe",
    "title": "Research Analyst",
    "bio": "5 years experience...",
    "skills": ["quantitative", "analysis"],
    "expertise_areas": ["healthcare"],
    "hourly_rate": 150.00,
    "email": "john@company.com"
  }'
```

## Development

### Running Tests

```bash
cd backend
pytest
```

### Database Migrations

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black backend/

# Lint
ruff check backend/
```

## Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Generate secure JWT_SECRET_KEY
- [ ] Use strong database password
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Set up proper firewall rules
- [ ] Use AWS S3 instead of MinIO
- [ ] Enable database backups
- [ ] Set up monitoring and logging
- [ ] Review API rate limits

### AWS Deployment Example

```bash
# Update .env for production
USE_MINIO=false
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_BUCKET_NAME=your-bucket-name
AWS_REGION=us-east-1
ENVIRONMENT=production
DEBUG=false
```

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Review API docs: http://localhost:8000/docs
- Verify environment variables are set correctly

## License

Proprietary - All rights reserved
