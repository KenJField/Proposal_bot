# Proposal Bot - LangChain Deep Agent System

An intelligent, autonomous proposal generation system for market research firms built using LangChain's Deep Agents pattern and LangGraph workflow orchestration.

## Overview

Proposal Bot automates the complex process of creating market research proposals by orchestrating multiple AI agents that work together to:

1. **Prepare and validate briefs** - Analyze incoming RFPs, identify missing information, and gather context
2. **Generate proposals** - Create detailed project plans, match resources, and validate with stakeholders
3. **Learn continuously** - Monitor communications and update knowledge base for improved future proposals

## Key Features

### 🤖 Multi-Agent Architecture

- **Brief Preparation Agent**: Analyzes briefs, spawns sub-agents for research and communication, validates completeness
- **Proposal Agent**: Creates project plans, resources projects, spawns validation sub-agents, generates proposals
- **Background Memory Agent**: Monitors emails, extracts knowledge, updates pricing/capabilities

### 🔄 LangGraph Workflow Orchestration

- State-machine workflow with checkpoints for human-in-the-loop interactions
- Handles clarifications, validations, and approvals seamlessly
- Resumes from checkpoints when responses are received

### 🛠️ Deep Agent Capabilities

**Built-in (from `create_deep_agent`):**
- **Planning Tools**: `write_todos` for task breakdown and progress tracking (automatic)
- **File Tools**: `ls`, `read_file`, `write_file`, `edit_file` for context management (automatic)
- **Subagent Spawning**: `task` tool for delegating to specialized sub-agents (automatic)

**Custom Tools:**
- **Email Tools**: Gmail integration for automated communication
- **Resource Tools**: Google Sheets integration for staff and vendor data
- **Knowledge Tools**: Memory management for continuous learning

### 📊 Business Logic

- Sophisticated pricing calculator with markup, discounts, and margin protection
- Professional proposal formatter with standardized structure
- Resource matching and validation workflow

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Incoming Brief                          │
│              (Email, RFP, Manual Entry)                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Brief Preparation Agent                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • Analyze brief quality                               │  │
│  │ • Spawn sub-agents:                                   │  │
│  │   - Email communicator (sales rep clarification)     │  │
│  │   - Project researcher (past projects)               │  │
│  │   - Web researcher (client profiles)                 │  │
│  │   - CRM integrator (client data)                     │  │
│  │ • Validate brief completeness                         │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Proposal Agent                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • Create project plan and methodology                 │  │
│  │ • Search resources (Google Sheets):                   │  │
│  │   - Staff profiles and availability                   │  │
│  │   - Vendor capabilities and pricing                   │  │
│  │   - Company capabilities                              │  │
│  │ • Spawn resource validation sub-agents (email)        │  │
│  │ • Select project lead                                 │  │
│  │ • Spawn lead validation sub-agent                     │  │
│  │ • Apply pricing rules and business logic              │  │
│  │ • Generate formatted proposal                         │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│             Background Memory Agent                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • Monitor email responses                             │  │
│  │ • Extract and update knowledge:                       │  │
│  │   - Vendor pricing updates                            │  │
│  │   - Staff capabilities and skills                     │  │
│  │   - Successful proposal patterns                      │  │
│  │ • Improve future proposals                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL with pgvector (optional, for production)
- Redis (optional, for production)
- Google Workspace account with Gmail and Sheets API access
- Anthropic API key

### Setup

1. **Clone the repository**
   ```bash
   cd Proposal_bot
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Set up Google Workspace**
   - Enable Gmail and Google Sheets APIs
   - Create OAuth credentials
   - Add credentials to `.env`

5. **Upload test data to Google Sheets**
   - Create Google Sheets for staff, vendors, and pricing
   - Import CSV templates from `data/google_sheets_templates/`
   - Add Sheet IDs to `.env`

## Usage

### Running a Proposal Workflow

```bash
python main.py data/briefs/example_brief_good_quality.json
```

This will:
1. Load the brief
2. Run the Brief Preparation Agent
3. Generate the proposal via Proposal Agent
4. Update knowledge via Background Memory Agent
5. Save results to `workflow_result_*.json`

### Testing Different Brief Qualities

```bash
# Good quality brief (complete information)
python main.py data/briefs/example_brief_good_quality.json

# Medium quality brief (missing some details)
python main.py data/briefs/example_brief_medium_quality.json

# Poor quality brief (very incomplete)
python main.py data/briefs/example_brief_poor_quality.json
```

### Resuming from Checkpoint

When the workflow pauses for human input (clarifications, validations), you can resume:

```python
from proposal_bot.graphs.proposal_workflow import ProposalWorkflow

workflow = ProposalWorkflow()
result = workflow.resume_workflow(
    project_id="project_brief_2024_001",
    updates={
        "awaiting_clarification": False,
        "brief": updated_brief_data,
    }
)
```

## Project Structure

```
Proposal_bot/
├── proposal_bot/
│   ├── agents/                 # Deep Agent implementations
│   │   ├── brief_preparation_agent.py
│   │   ├── proposal_agent.py
│   │   └── background_memory_agent.py
│   ├── config/                 # Configuration
│   │   └── settings.py
│   ├── graphs/                 # LangGraph workflows
│   │   └── proposal_workflow.py
│   ├── schemas/                # Pydantic data models
│   │   ├── brief.py
│   │   ├── project.py
│   │   ├── proposal.py
│   │   ├── resource.py
│   │   └── validation.py
│   ├── services/               # Business logic services
│   │   ├── google_sheets.py
│   │   ├── pricing_calculator.py
│   │   └── proposal_formatter.py
│   └── tools/                  # Agent tools
│       ├── email_tools.py
│       ├── file_tools.py
│       ├── knowledge_tools.py
│       ├── planning_tools.py
│       └── resource_tools.py
├── data/                       # Test data
│   ├── briefs/                 # Example briefs
│   └── google_sheets_templates/ # CSV templates for Google Sheets
├── main.py                     # Main entry point
├── pyproject.toml             # Package configuration
└── README.md                  # This file
```

## Configuration

### Environment Variables

Key configuration in `.env`:

```bash
# Anthropic
ANTHROPIC_API_KEY=your_key

# LangSmith (for deployment and monitoring)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key
LANGCHAIN_PROJECT=proposal-bot

# Google Workspace
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token

# Google Sheets IDs
STAFF_PROFILES_SHEET_ID=your_sheet_id
PRICING_SHEET_ID=your_sheet_id
VENDOR_RELATIONSHIPS_SHEET_ID=your_sheet_id

# Gmail
GMAIL_USER_EMAIL=proposals@yourcompany.com
```

## Workflow States

The LangGraph workflow progresses through these states:

1. **brief_preparation** - Analyze and validate brief
2. **check_clarification** - Determine if clarification needed
3. **await_clarification** - Human-in-the-loop (if needed)
4. **proposal_generation** - Generate project plan
5. **resource_validation** - Validate resources via email
6. **await_validation** - Human-in-the-loop for responses
7. **lead_validation** - Validate with project lead
8. **await_lead_approval** - Human-in-the-loop for approval
9. **finalize_proposal** - Apply business logic and format
10. **update_memory** - Update knowledge base
11. **complete** - Workflow complete

## Deployment

### LangSmith Deployment

For production deployment on LangSmith (formerly LangGraph Cloud):

1. **Prepare deployment**
   ```bash
   # Ensure all dependencies are in pyproject.toml
   # Configure LangSmith API key in .env
   ```

2. **Deploy to LangSmith**
   - Connect GitHub repository to LangSmith
   - Configure environment variables
   - Deploy with 1-click

3. **Monitor**
   - Use LangSmith tracing to monitor agent behavior
   - Review checkpoints and state transitions
   - Analyze performance and costs

### Docker Deployment (Alternative)

```bash
# Build image
docker build -t proposal-bot .

# Run container
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  proposal-bot
```

## Deep Agents Pattern

This implementation uses LangChain's official **`create_deep_agent`** API from the `deepagents` package.

### Creating a Deep Agent

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

# Initialize LLM
llm = ChatAnthropic(model="claude-sonnet-4-5-20250929")

# Create deep agent with built-in capabilities
agent = create_deep_agent(
    model=llm,
    tools=[...],  # Custom tools only (planning & file tools are automatic)
    system_prompt="You are a research proposal agent..."
)

# Invoke the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Create a proposal..."}]
})
```

### Built-in Capabilities

Deep agents automatically provide:

**1. Planning Tool (`write_todos`)**
Agents break down complex tasks:
```python
# This tool is built-in - no need to create it manually
write_todos([
    {"content": "Analyze brief", "status": "in_progress", "activeForm": "Analyzing brief"},
    {"content": "Search staff", "status": "pending", "activeForm": "Searching staff"}
])
```

**2. File System Tools**
Agents manage context automatically:
```python
# These tools are built-in
ls(".")
read_file("project_plan.md")
write_file("analysis.txt", content)
edit_file("draft.md", old_text, new_text)
```

**3. Subagent Spawning (`task`)**
Agents delegate to specialists:
```python
# Built-in task tool for spawning subagents
task(task_description="Validate vendor pricing", ...)
```

**4. Detailed System Prompts**
Each agent has specialized prompts configured via the `system_prompt` parameter.

## Knowledge Management

The Background Memory Agent continuously learns:

### Vendor Pricing Updates

```python
{
  "vendor_id": "vendor_003",
  "confirmed_rate": 48.00,  # Updated from 45.00
  "effective_date": "2024-06-01"
}
```

### Staff Capabilities

```python
{
  "staff_id": "staff_005",
  "new_skills": ["advanced machine learning", "LLM fine-tuning"],
  "successful_projects": 48  # Incremented
}
```

### Successful Patterns

```python
{
  "project_type": "customer_satisfaction",
  "methodology": "mixed_methods",
  "team_structure": {...},
  "client_feedback": "Excellent - won follow-on work"
}
```

## Testing

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=proposal_bot
```

### Test Scenarios

The example briefs test different scenarios:

- **Good Quality**: Complete brief, smooth workflow
- **Medium Quality**: Missing details, triggers clarification
- **Poor Quality**: Very incomplete, extensive clarification needed

## Performance

### Model Selection

- **Default Model**: `claude-3-5-sonnet-20241022` for complex reasoning
- **Fast Model**: `claude-3-5-haiku-20241022` for background processing
- **Temperature**: 0.7 for creative proposal generation, 0.3 for data extraction

### Cost Optimization

- Use fast model for routine tasks (email monitoring, data extraction)
- Use default model for complex reasoning (planning, proposal generation)
- Leverage file system to reduce context window usage
- Cache resource data in Google Sheets (read once per workflow)

## Limitations

### Current Implementation

- Sub-agents are simulated (not full Deep Agent implementations)
- Email monitoring is not continuous (manual trigger required)
- CRM integration is placeholder
- Web research is not implemented

### Production Considerations

- Implement actual email polling/webhooks
- Add proper error handling and retries
- Implement rate limiting for APIs
- Add authentication and authorization
- Scale with message queues (Celery/Redis)

## Future Enhancements

### Planned Features

1. **Advanced Sub-Agents**: Full Deep Agent implementation for sub-agents
2. **Real-time Email Monitoring**: Continuous background processing
3. **CRM Integration**: Salesforce, HubSpot connectors
4. **Web Research**: Automated client and market research
5. **Document Generation**: PDF proposals, PowerPoint presentations
6. **Multi-language Support**: International proposal generation
7. **A/B Testing**: Experiment with different proposal approaches
8. **Predictive Win Rates**: ML model to predict proposal success

## Resources

### Documentation

- [LangChain Deep Agents](https://blog.langchain.com/deep-agents/)
- [LangGraph Documentation](https://www.langchain.com/langgraph)
- [LangSmith Deployment](https://www.langchain.com/langsmith/deployment)

### Related Projects

- [LangChain DeepAgents GitHub](https://github.com/langchain-ai/deepagents)
- [LangGraph Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For questions or issues:

- Open an issue on GitHub
- Contact: support@example.com
- Documentation: [Link to docs]

---

**Built with LangChain Deep Agents** 🦜🔗
