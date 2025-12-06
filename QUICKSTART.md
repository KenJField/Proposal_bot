# Quick Start Guide

Get Proposal Bot up and running in 15 minutes!

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] Anthropic API key ([Get one here](https://console.anthropic.com/))
- [ ] Google Workspace account
- [ ] Git installed

## Step 1: Clone and Install (2 minutes)

```bash
cd Proposal_bot
pip install -e .
```

## Step 2: Configure Environment (5 minutes)

### 2.1 Copy environment template

```bash
cp .env.example .env
```

### 2.2 Add your Anthropic API key

Edit `.env` and add:
```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 2.3 Configure Google Workspace (Optional for first run)

For now, you can use placeholder values:
```bash
GOOGLE_CLIENT_ID=placeholder
GOOGLE_CLIENT_SECRET=placeholder
GOOGLE_REFRESH_TOKEN=placeholder
STAFF_PROFILES_SHEET_ID=placeholder
PRICING_SHEET_ID=placeholder
VENDOR_RELATIONSHIPS_SHEET_ID=placeholder
GMAIL_USER_EMAIL=placeholder@example.com
```

**Note:** The system will work in simulation mode without real Google integrations. To enable full functionality, follow the [Google Workspace Setup Guide](./docs/GOOGLE_SETUP.md).

## Step 3: Run Your First Workflow (3 minutes)

```bash
python main.py data/briefs/example_brief_good_quality.json
```

You should see:

```
================================================================================
PROPOSAL BOT - LangChain Deep Agent System
================================================================================

📋 Loading brief from: data/briefs/example_brief_good_quality.json
✓ Brief loaded: Customer Satisfaction and Product Usage Study
  Client: TechCorp Industries
  Contact: Jane Smith (jane.smith@techcorp.com)

🚀 Initializing proposal workflow...
✓ Workflow initialized

⚙️  Running workflow...
...
✅ Workflow completed!
```

## Step 4: Explore the Results (5 minutes)

### 4.1 Check the output file

```bash
ls -l workflow_result_*.json
cat workflow_result_project_brief_2024_001.json
```

### 4.2 Explore the agent workspace

```bash
ls -la .agent_workspace/
cat .agent_workspace/todos.json
```

### 4.3 Try different brief qualities

```bash
# Medium quality - triggers clarification workflow
python main.py data/briefs/example_brief_medium_quality.json

# Poor quality - extensive clarification needed
python main.py data/briefs/example_brief_poor_quality.json
```

## Understanding the Output

The workflow generates:

1. **Workflow Result JSON** (`workflow_result_*.json`)
   - Complete workflow state
   - All agent outputs
   - Messages and status

2. **Agent Workspace** (`.agent_workspace/`)
   - Todo lists showing agent planning
   - File outputs from agents
   - Knowledge base updates

3. **Checkpoints** (`checkpoints.db`)
   - SQLite database with workflow checkpoints
   - Enables resuming from human-in-the-loop points

## Next Steps

### Enable Google Integrations

Follow [Google Workspace Setup Guide](./docs/GOOGLE_SETUP.md) to:
- Set up Gmail API for automated emails
- Create Google Sheets for resource data
- Configure OAuth credentials

### Customize for Your Business

1. **Update test data**
   - Edit `data/google_sheets_templates/*.csv`
   - Add your actual staff profiles
   - Add your vendor relationships
   - Update pricing models

2. **Customize prompts**
   - Edit agent prompts in `proposal_bot/agents/`
   - Adjust for your industry and style
   - Add company-specific guidelines

3. **Configure business logic**
   - Update `proposal_bot/services/pricing_calculator.py`
   - Modify markup and discount rules
   - Adjust proposal formatting

### Deploy to Production

See [Deployment Guide](./docs/DEPLOYMENT.md) for:
- LangSmith deployment
- Docker deployment
- Production configuration
- Monitoring and observability

## Troubleshooting

### Import Errors

```bash
# Reinstall in development mode
pip install -e .
```

### Module Not Found

```bash
# Make sure you're in the Proposal_bot directory
pwd
# Should show: .../Proposal_bot

# Install dependencies
pip install -e .
```

### API Key Issues

```bash
# Verify your .env file exists and has correct key
cat .env | grep ANTHROPIC_API_KEY
```

### Google API Errors

For the initial test run, Google integrations are simulated. Real integration requires setup - see [Google Workspace Setup Guide](./docs/GOOGLE_SETUP.md).

## Getting Help

- **Documentation**: See [README.md](./README.md)
- **Issues**: Open an issue on GitHub
- **Questions**: Contact support@example.com

## What's Next?

Explore these guides:

- [Architecture Deep Dive](./docs/ARCHITECTURE.md)
- [Agent Development Guide](./docs/AGENT_DEVELOPMENT.md)
- [Tool Development Guide](./docs/TOOL_DEVELOPMENT.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)

---

**Welcome to Proposal Bot!** 🎉

You're now ready to automate proposal generation with LangChain Deep Agents.
