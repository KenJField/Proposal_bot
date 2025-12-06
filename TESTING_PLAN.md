# Multi-Agent Market Research Proposal Generator - User Testing Plan

## Overview

This testing plan provides comprehensive validation of all system features for the Multi-Agent Market Research Proposal Generator. Each test case includes specific inputs, expected outputs, and validation criteria.

**Prerequisites:**
- All dependencies installed (`pip install -r requirements.txt`)
- PostgreSQL database with pgvector extension created
- Redis server running
- Environment variables configured in `.env` file
- API keys for Google Gemini, Anthropic Claude, Google Search, and Notion

**System Startup:**
```bash
# Terminal 1: API Server
python main.py

# Terminal 2: Celery Worker
celery -A app.core.celery_app worker --loglevel=info --concurrency=2

# Terminal 3: Celery Beat (Scheduler)
celery -A app.core.celery_app beat --loglevel=info
```

---

## 1. API Health and Monitoring Tests

### 1.1 Basic Health Check
**Endpoint:** `GET /health`
**Purpose:** Verify basic system health

**Test Steps:**
1. Send GET request to `/health`
2. Check response status and content

**Expected Output:**
```json
{
  "status": "healthy",
  "timestamp": 1703123456.789
}
```

**Validation:**
- ✅ HTTP 200 status code
- ✅ Response contains "healthy" status
- ✅ Timestamp is recent (within last minute)

### 1.2 Detailed Health Check
**Endpoint:** `GET /health/detailed`
**Purpose:** Comprehensive system health check

**Expected Output:**
```json
{
  "status": "healthy",
  "timestamp": 1703123456.789,
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection OK"
    },
    "redis": {
      "status": "healthy",
      "version": "7.2.0",
      "connected_clients": 5
    },
    "llm_providers": {
      "status": "healthy",
      "providers": {
        "gemini": {"status": "healthy"},
        "claude": {"status": "healthy"}
      }
    },
    "email": {
      "status": "healthy",
      "message": "Email services configured"
    }
  }
}
```

### 1.3 Metrics Endpoint
**Endpoint:** `GET /metrics`
**Purpose:** Prometheus metrics validation

**Expected Output:**
- Plain text response with Prometheus format
- Contains metrics like:
  ```
  proposal_bot_requests_total{method="GET",endpoint="/health",status="200"} 1.0
  proposal_bot_agent_executions_total{agent_name="brief_review",status="completed"} 0.0
  ```

### 1.4 System Status
**Endpoint:** `GET /status`
**Purpose:** System overview and statistics

**Expected Output:**
```json
{
  "status": "operational",
  "timestamp": 1703123456.789,
  "version": "1.0.0",
  "environment": "development",
  "work_queue_length": 0,
  "projects_by_status": {},
  "agents_registered": 7
}
```

---

## 2. Core RFP Processing Tests

### 2.1 Submit RFP - Basic Functionality
**Endpoint:** `POST /rfp/submit`
**Purpose:** Test basic RFP submission and storage

**Test Input:**
```bash
curl -X POST "http://localhost:8000/rfp/submit" \
  -F "file=@sample_rfp.pdf" \
  -F "client_name=TechCorp Solutions" \
  -F "opportunity_id=RFP-2024-001"
```

**Sample RFP Content (create sample_rfp.pdf):**
```
Market Research RFP - Consumer Electronics

Client: TechCorp Solutions
Industry: Consumer Electronics

Objectives:
- Understand smartphone purchasing behavior
- Identify key decision drivers
- Test concept acceptance for new device features

Methodology Requirements:
- Online survey: 2,000 respondents
- Focus groups: 6 groups of 8 participants
- In-depth interviews: 15 industry experts

Timeline: 12 weeks total
Budget: $85,000 - $120,000
```

**Expected Output:**
```json
{
  "project_id": 1,
  "status": "submitted",
  "message": "RFP submitted successfully - processing started"
}
```

**Validation:**
- ✅ HTTP 200 status code
- ✅ Returns project_id (integer)
- ✅ Status shows "submitted"
- ✅ Check database: project created with correct metadata

### 2.2 Submit RFP - Invalid Data
**Endpoint:** `POST /rfp/submit`
**Purpose:** Test input validation

**Test Input:**
```bash
curl -X POST "http://localhost:8000/rfp/submit" \
  -F "client_name=" \
  -F "opportunity_id=RFP-2024-001"
```

**Expected Output:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "file"],
      "msg": "Field required"
    }
  ]
}
```

**Validation:**
- ✅ HTTP 422 status code
- ✅ Proper validation error messages

### 2.3 Get Project Status
**Endpoint:** `GET /project/{project_id}`
**Purpose:** Verify project status retrieval

**Test Steps:**
1. Submit RFP (get project_id from 2.1)
2. Query project status immediately
3. Wait 30 seconds and query again

**Expected Initial Output:**
```json
{
  "id": 1,
  "title": "RFP from TechCorp Solutions",
  "client_name": "TechCorp Solutions",
  "status": "received",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z",
  "estimated_value": null,
  "project_lead": null
}
```

**Expected After Processing:**
```json
{
  "id": 1,
  "title": "RFP from TechCorp Solutions",
  "client_name": "TechCorp Solutions",
  "status": "analyzing",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:05Z",
  "estimated_value": {"min": 85000, "max": 120000},
  "project_lead": null
}
```

### 2.4 List All Projects
**Endpoint:** `GET /projects`
**Purpose:** Test project listing functionality

**Expected Output:**
```json
[
  {
    "id": 1,
    "title": "RFP from TechCorp Solutions",
    "client_name": "TechCorp Solutions",
    "status": "analyzing",
    "created_at": "2024-01-01T10:00:00Z"
  }
]
```

---

## 3. Agent Workflow Tests

### 3.1 Brief Review Agent Processing
**Purpose:** Test RFP analysis and requirements extraction

**Test Steps:**
1. Submit RFP (from 2.1)
2. Monitor project status until "requirements_ready"
3. Check database for analysis results

**Expected Database State:**
```sql
-- Check project.requirements field
{
  "brief_analysis": {
    "analysis": {
      "client_name": "TechCorp Solutions",
      "objectives": ["Understand smartphone purchasing behavior", "..."],
      "methodology_requirements": ["survey", "focus groups", "interviews"],
      "timeline": {"total_weeks": 12},
      "budget_range": {"min": 85000, "max": 120000}
    },
    "go_no_go": {
      "score": 85,
      "recommendation": "GO",
      "factors": ["Strong methodology fit", "..."]
    },
    "clarification_questions": [],
    "recommended_lead": {
      "name": "Sarah Johnson",
      "confidence_score": 0.9
    }
  }
}
```

**Validation:**
- ✅ Project status changes to "requirements_ready"
- ✅ Analysis contains all required fields
- ✅ Go/no-go score calculated
- ✅ Clarification questions generated (if any)

### 3.2 Planning Agent Resource Matching
**Purpose:** Test resource discovery and validation orchestration

**Test Steps:**
1. Wait for project status to reach "validating"
2. Check planning results in database

**Expected Database State:**
```sql
-- Check project.plan field
{
  "resource_matches": {
    "matched_resources": [
      {
        "id": 1,
        "name": "Sarah Johnson",
        "capabilities": ["survey", "focus_groups"],
        "overall_score": 88,
        "similarity_score": 0.85
      }
    ],
    "resource_gaps": []
  },
  "validations_triggered": [
    {
      "validation_id": 1,
      "question": "Do you have experience conducting online surveys?",
      "priority": "high"
    }
  ]
}
```

**Validation:**
- ✅ Resources matched based on methodology requirements
- ✅ Validation emails triggered (check Celery logs)
- ✅ Project status advances to "planning"

### 3.3 Email Validation Workflow
**Purpose:** Test email sending and response processing

**Test Steps:**
1. Check that validation emails are sent (monitor Celery logs)
2. Simulate email response (if possible with test setup)
3. Check validation status updates

**Expected Email Content:**
```
Subject: Capability Validation - Consumer Electronics Study

Dear Team Member,

We are preparing a proposal and need to validate your capabilities...

Question: Do you have experience conducting online surveys?

Please reply with Yes/No/Limited with additional context.
```

**Validation:**
- ✅ Email sent successfully (check SMTP logs)
- ✅ Thread tracking works (check Redis)
- ✅ Deduplication prevents duplicate sends

### 3.4 Go-to-Market Proposal Generation
**Purpose:** Test proposal creation and pricing

**Test Steps:**
1. Wait for project status to reach "draft_ready"
2. Check proposal outline in database

**Expected Proposal Structure:**
```sql
-- Check project.requirements.proposal_outline
{
  "title": "Market Research Proposal - TechCorp Solutions",
  "executive_summary": "Comprehensive research study...",
  "methodology": {
    "approach": "Mixed-method quantitative and qualitative",
    "sample_size": "2,000 survey respondents + 48 focus group participants"
  },
  "timeline": {
    "total_weeks": 12,
    "phases": [...]
  },
  "pricing": {
    "total_price": 97500,
    "breakdown": {
      "resources": 65000,
      "vendor": 15000,
      "overhead": 10000,
      "contingency": 7500
    }
  },
  "team": ["Sarah Johnson", "Mike Chen"],
  "status": "ready_for_review"
}
```

### 3.5 Notion Workspace Updates
**Purpose:** Test real-time workspace visibility

**Test Steps:**
1. Check Notion page creation after analysis
2. Verify project plan database creation
3. Test status updates

**Expected Notion Content:**
- RFP Analysis page with structured sections
- Project Plan page with phase database
- Real-time status updates as workflow progresses

**Validation:**
- ✅ Pages created successfully (check Notion API logs)
- ✅ Proper error handling if API unavailable
- ✅ Fallback to mock mode works

---

## 4. External Integration Tests

### 4.1 Web Research Service
**Purpose:** Test company research functionality

**Test Code:**
```python
from app.services.web_research import web_research_service
import asyncio

async def test_research():
    result = await web_research_service.search_company_info("Apple Inc")
    print("Company research result:", result)

asyncio.run(test_research())
```

**Expected Output:**
```json
{
  "name": "Apple Inc",
  "industry": "Consumer Electronics",
  "website": "apple.com",
  "description": "Apple Inc. is an American multinational technology company...",
  "headquarters": "Cupertino, California",
  "employee_count": "150,000+ employees",
  "founded_year": 1976,
  "sources": ["https://en.wikipedia.org/wiki/Apple_Inc", "..."],
  "last_updated": "2024-01-01T00:00:00Z"
}
```

### 4.2 Knowledge Base Search
**Purpose:** Test semantic search functionality

**Test Code:**
```python
from app.knowledge.kb import KnowledgeBase
from app.database.connection import async_session_factory
import asyncio

async def test_kb():
    async with async_session_factory() as db:
        kb = KnowledgeBase(db)
        results = await kb.search_resources("experienced survey researcher", top_k=3)
        print("KB search results:", results)

asyncio.run(test_kb())
```

**Expected Output:**
```json
[
  {
    "id": 1,
    "name": "Sarah Johnson",
    "capabilities": ["survey", "quantitative_research"],
    "similarity_score": 0.89,
    "confidence_score": 0.85
  }
]
```

### 4.3 LLM Integration Test
**Purpose:** Test AI provider functionality

**Test Code:**
```python
from app.core.llm import llm_manager, Provider
import asyncio

async def test_llm():
    prompt = "Analyze this market research requirement: consumer survey with 1000 respondents"
    response = await llm_manager.generate(
        prompt=prompt,
        provider=Provider.GEMINI,
        temperature=0.3
    )
    print("LLM response:", response.content[:200])

asyncio.run(test_llm())
```

**Expected Output:**
- Meaningful analysis of survey requirements
- Proper response structure with content, usage, and finish_reason

---

## 5. Error Handling and Edge Cases

### 5.1 Database Connection Failure
**Purpose:** Test graceful degradation

**Test Steps:**
1. Stop PostgreSQL server
2. Make API request
3. Check error response

**Expected Output:**
```json
{
  "detail": "Database connection error"
}
```

**Validation:**
- ✅ Proper error messages
- ✅ No system crashes
- ✅ Graceful error handling

### 5.2 External API Failure
**Purpose:** Test fallback mechanisms

**Test Steps:**
1. Remove/disable API keys temporarily
2. Trigger web research or LLM calls
3. Check fallback behavior

**Expected Behavior:**
- Services return mock/default data
- System continues operating
- Warnings logged but no failures

### 5.3 Invalid File Upload
**Purpose:** Test file validation

**Test Input:**
```bash
curl -X POST "http://localhost:8000/rfp/submit" \
  -F "file=@invalid_file.exe" \
  -F "client_name=Test Client"
```

**Expected Output:**
```json
{
  "detail": "Invalid file type. Only PDF files are accepted."
}
```

### 5.4 Concurrent Request Handling
**Purpose:** Test system under load

**Test Steps:**
1. Submit multiple RFPs simultaneously
2. Monitor system performance
3. Check queue processing

**Expected Behavior:**
- All requests processed successfully
- No race conditions
- Proper resource utilization

---

## 6. Performance and Monitoring Tests

### 6.1 Response Time Validation
**Purpose:** Ensure acceptable API performance

**Test Script:**
```bash
# Test API response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/health"
```

**Expected Performance:**
- Health check: < 100ms
- Project status: < 500ms
- RFP submission: < 2000ms (includes file processing)

### 6.2 Agent Execution Monitoring
**Purpose:** Verify agent performance tracking

**Test Steps:**
1. Submit RFP and monitor logs
2. Check agent execution metrics

**Expected Logs:**
```
INFO - Starting execution of brief_review for project 1
INFO - Agent execution completed: brief_review - Duration: 2.3s
```

**Expected Metrics:**
```
proposal_bot_agent_executions_total{agent_name="brief_review",status="completed"} 1.0
proposal_bot_agent_execution_duration_seconds_sum{agent_name="brief_review"} 2.3
```

### 6.3 Queue Monitoring
**Purpose:** Test Celery task processing

**Test Steps:**
1. Submit multiple RFPs quickly
2. Monitor Celery worker logs
3. Check queue status

**Expected Behavior:**
- Tasks processed in order
- No task loss
- Proper error handling and retries

---

## 7. Data Persistence Tests

### 7.1 Project Data Integrity
**Purpose:** Verify data is properly stored and retrieved

**Test Steps:**
1. Submit RFP and wait for processing
2. Query project data multiple times
3. Verify data consistency

**Validation:**
- ✅ All project fields populated correctly
- ✅ Related data (analysis, plan, proposal) linked properly
- ✅ No data corruption or loss

### 7.2 Audit Trail Verification
**Purpose:** Test state transition logging

**Test Steps:**
1. Submit RFP and monitor status changes
2. Check state transition logs

**Expected Log Entries:**
```sql
-- Check state_transition_logs table
{
  "project_id": 1,
  "from_status": "received",
  "to_status": "analyzing",
  "agent_name": "orchestrator",
  "reasoning": "Following deterministic transition"
}
```

---

## 8. Integration Test Suite

### 8.1 Full End-to-End Workflow
**Purpose:** Complete RFP-to-proposal process

**Test Steps:**
1. Submit RFP
2. Monitor workflow: received → analyzing → requirements_ready → validating → planning → draft_ready → review_ready → approved → generating → final_ready → sent
3. Verify all intermediate states
4. Check final deliverables

**Expected Final State:**
- Project status: "sent"
- Proposal generated and delivered
- All audit logs complete
- Email notifications sent

### 8.2 Cross-Agent Communication
**Purpose:** Test agent interactions

**Test Steps:**
1. Submit RFP requiring clarification
2. Monitor email exchange
3. Verify state changes based on responses

**Expected Behavior:**
- Clarification emails sent
- Project status changes to "needs_clarification"
- Response processing updates project data
- Workflow resumes correctly

---

## Test Execution Checklist

- [ ] Environment setup complete
- [ ] All dependencies installed
- [ ] Database and Redis running
- [ ] API keys configured
- [ ] Services started successfully
- [ ] Basic health checks pass
- [ ] RFP submission works
- [ ] Agent workflow executes
- [ ] External integrations functional
- [ ] Error scenarios handled
- [ ] Performance acceptable
- [ ] Data persistence verified
- [ ] End-to-end workflow complete

## Troubleshooting Guide

### Common Issues:

**"Module not found" errors:**
- Run `python setup.py` to install dependencies
- Check Python path and virtual environment

**Database connection errors:**
- Ensure PostgreSQL is running
- Verify connection string in `.env`
- Check pgvector extension is installed

**Redis connection errors:**
- Ensure Redis server is running on correct port
- Check Redis URL in `.env`

**API key errors:**
- Verify all required API keys are set in `.env`
- Check API key validity and permissions

**Email sending failures:**
- Verify SMTP credentials in `.env`
- Check network connectivity to SMTP server

**Agent execution timeouts:**
- Check Celery worker is running
- Monitor Celery logs for errors
- Verify database connections in workers

### Debug Commands:

```bash
# Check service status
curl http://localhost:8000/health

# View application logs
tail -f logs/app.log

# Check Celery status
celery -A app.core.celery_app inspect active

# Monitor database
psql -d proposal_bot -c "SELECT status, COUNT(*) FROM projects GROUP BY status;"

# Check Redis
redis-cli ping
redis-cli KEYS "*"
```

This comprehensive testing plan ensures all system features are validated and provides clear debugging guidance for any issues encountered during setup and operation.
