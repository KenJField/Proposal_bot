# Multi-Agent Market Research Proposal Generator - Requirements Document

## Executive Summary

An intelligent multi-agent system that automates the market research proposal process from RFP receipt through final PowerPoint delivery. The system uses specialized agents coordinated by an orchestrator to analyze briefs, plan projects, validate resources, and generate professional proposals—reducing proposal time from days to hours while maintaining quality and accuracy.

---

## Agent Architecture

### Orchestrator Agent
**Purpose:** Central coordinator that manages workflow state and delegates tasks to specialized agents

**Responsibilities:**
- Monitor overall project state in PostgreSQL
- Decide which agent should act next based on project status and dependencies
- Handle state transitions (received → analyzing → validating → planning → ready)
- Manage timeout conditions and escalations
- Coordinate concurrent operations (e.g., multiple validations running in parallel)
- Handle error recovery and retry logic
- Track completion conditions and trigger next workflow steps
- Maintain work queue priorities based on deadlines, client importance, and waiting time

**Key Decision Points:**
- When to proceed from analysis to planning
- When to wait for validations vs. proceed with partial information
- When to escalate to human for blocked projects
- Which provider to use for each task (Gemini for speed, Claude for complexity)

**Inputs:** Project state, validation results, agent outputs, timeout events
**Outputs:** Task assignments to specialized agents, state updates, escalation notifications

---

### Email Agent
**Purpose:** Handle all email communication with clients, team members, and vendors

**Responsibilities:**
- **Sending:**
  - Draft contextual emails using templates and AI generation
  - Send validation requests to team members
  - Send clarification questions to clients (via sales staff)
  - Send availability confirmations to resources
  - Deliver final proposals
  - Track sent emails for deduplication (don't email same person about same thing within 48 hours)
  
- **Receiving:**
  - Monitor inbox via IMAP (check every 60 seconds)
  - Match responses to original threads using message IDs and References headers
  - Parse email content and extract structured information
  - Route parsed responses to appropriate handlers (validation complete, client clarification, etc.)
  - Handle out-of-office and error responses
  
- **Thread Management:**
  - Maintain conversation context across multiple exchanges
  - Track which emails are awaiting responses
  - Register thread IDs in Redis for fast lookup
  - Handle timeout notifications (72 hours default for validations)

**Inputs:** Email composition requests, IMAP inbox, thread tracking data
**Outputs:** Sent emails, parsed responses, validation results, client answers
**Tools:** SMTP, IMAP, Redis (thread tracking), email template library

---

### Brief Review Agent
**Purpose:** Analyze incoming research briefs and decompose into structured project requirements

**Responsibilities:**
- **Analysis:**
  - Extract key information (methodologies, sample size, timeline, budget, deliverables)
  - Identify project type and complexity level
  - Detect ambiguities and missing critical information
  - Calculate go/no-go score based on firm capabilities and strategic fit
  
- **Context Enrichment:**
  - Query knowledge base for past projects with this client
  - Search documents (past proposals, case studies) for relevant context
  - Perform web research on client (industry, recent news, competitors)
  - Identify client preferences and past feedback from document history
  
- **Gap Analysis:**
  - Identify missing requirements (budget not specified, timeline unclear)
  - Formulate specific clarification questions for client
  - Prioritize questions by criticality (blocking vs. nice-to-have)
  - Draft questions in client-appropriate language (via sales staff)
  
- **Requirements Output:**
  - Generate structured requirements document
  - Include confidence scores for each requirement
  - Flag which requirements need validation
  - Recommend project lead based on methodology expertise and availability
  - Create Notion page with analysis summary

**Inputs:** RFP email/document, client history from KB, past proposals, web research results
**Outputs:** Structured requirements, clarification questions, go/no-go recommendation, Notion analysis page
**Tools:** Knowledge Base search, document search, web research, LLM (Claude for complex analysis)
**Provider:** Claude Sonnet (complex reasoning required)

---

### Planning Agent
**Purpose:** Create detailed project plans by matching requirements to available resources

**Responsibilities:**
- **Resource Discovery:**
  - Query knowledge base for resources with required capabilities
  - Perform semantic search across team bios and past project documents
  - Calculate resource match scores based on capability confidence and project fit
  - Identify gaps where no suitable internal resource exists
  - Search for external consultants/vendors when needed (web research)
  
- **Validation Orchestration:**
  - Identify which resource attributes need validation (low confidence, stale data, critical path)
  - Prioritize validations (critical → high → medium → low)
  - Generate contextual validation questions for each resource
  - Trigger concurrent validation emails via Email Agent
  - Track validation status and wait for responses
  - Handle timeout conditions (try alternative methods, escalate, or proceed with caveats)
  - Update knowledge base when validations complete
  
- **Project Design:**
  - Allocate resources to project phases
  - Define scope of work for each resource
  - Calculate timeline based on resource availability and dependencies
  - Estimate costs using current pricing data
  - Identify dependencies and critical path
  - Generate alternative scenarios if primary resources unavailable
  
- **Iteration:**
  - Adapt plan as validation results arrive
  - Adjust timeline if key resources unavailable during preferred dates
  - Substitute resources when validations reveal capability gaps
  - Query project lead for design decisions (methodological choices, trade-offs)
  - Refine until plan meets all requirements within constraints

**Inputs:** Requirements from Brief Review Agent, knowledge base query results, validation responses, project lead feedback
**Outputs:** Detailed project plan with phases/resources/costs/timeline, validation tasks, design decision queries, updated KB entries
**Tools:** Knowledge Base (semantic + structured search), validation workflow, cost calculator
**Provider:** Claude Sonnet (complex planning and judgment calls)

---

### Go to Market Agent
**Purpose:** Transform project plan into client-ready proposal with pricing and business logic

**Responsibilities:**
- **Proposal Structure:**
  - Generate proposal outline from project plan
  - Organize into standard sections (Executive Summary, Methodology, Timeline, Deliverables, Team, Pricing)
  - Select relevant case studies and credentials
  - Draft compelling narrative around approach
  
- **Pricing Logic:**
  - Apply pricing rules (markup percentages, rounding conventions)
  - Calculate bundled pricing vs. itemized
  - Apply volume discounts where applicable
  - Include contingency buffers based on project risk
  - Format pricing for client presentation
  
- **Quality Assurance:**
  - Verify proposal addresses all requirements from brief
  - Check that methodology matches client needs
  - Ensure timeline is realistic given resource availability
  - Validate that team credentials match required expertise
  - Flag any gaps or inconsistencies for revision
  
- **Approval Workflow:**
  - Mark proposal outline ready for project lead review
  - Incorporate feedback from project lead
  - Track revision iterations
  - Flag when ready for PowerPoint generation

**Inputs:** Project plan, pricing rules, case study library, client requirements
**Outputs:** Proposal outline, pricing summary, QA notes, revision requests
**Provider:** Claude Sonnet or Gemini Flash (depends on complexity)

---

### Knowledge Agent
**Purpose:** Maintain knowledge base accuracy through continuous learning

**Responsibilities:**
- **Monitoring:**
  - Listen for validation results from Email Agent
  - Detect new information in client communications
  - Identify capability confirmations or corrections
  - Recognize pricing updates
  - Track availability changes
  
- **Knowledge Base Updates:**
  - Update resource attributes with new confidence scores
  - Add newly discovered capabilities
  - Correct outdated information
  - Create new resource entries (external consultants found via web research)
  - Add new documents (proposals, case studies) when referenced
  - Generate and update embeddings for semantic search
  
- **Learning & Pattern Recognition:**
  - Identify inference patterns (e.g., "advanced analytics" usually implies "conjoint analysis")
  - Suggest new inference rules based on confirmed patterns
  - Track which validation methods work best for which resource types
  - Calculate confidence score updates based on validation outcomes
  
- **Audit & Approval:**
  - Log all changes for human review
  - Flag high-impact changes (major capability additions, pricing changes)
  - Maintain change history with timestamps and sources
  - Queue proposed changes for human approval when confidence is low
  - Track which changes came from which sources (email, web, manual)

**Inputs:** Validation results, email content, web research findings, project outcomes
**Outputs:** Updated KB entries, new embeddings, change logs, approval requests
**Tools:** Knowledge Base, embedding generator (Google), change tracking system
**Provider:** Gemini Flash (simple extraction and updates) or Claude (complex inference decisions)

---

### Notion Agent
**Purpose:** Provide visibility into all agent activity via Notion workspace

**Responsibilities:**
- **Project Tracking:**
  - Create Notion page for each RFP with analysis summary
  - Generate project plan pages with phases as inline databases
  - Update project status as workflow progresses
  - Display validation status (pending, completed, timed out)
  - Show resource allocations and availability
  - Track proposal revisions and approvals
  
- **Opportunity Management:**
  - Maintain opportunities database with RFP tracking
  - Show pipeline stages (received → analyzing → proposal → sent → won/lost)
  - Display key metrics (estimated value, probability, timeline)
  - Link opportunities to project pages
  
- **Resource Management:**
  - Display resource availability calendar
  - Show current project assignments
  - Track utilization rates
  - Display capability matrices with confidence scores
  
- **Activity Feed:**
  - Log key events (RFP received, validation sent, plan approved)
  - Show agent decisions and reasoning
  - Display validation results as they arrive
  - Track email communications (sent/received)
  
- **User Interaction:**
  - Relay comments from project pages back to relevant agents
  - Capture approvals and feedback from project leads
  - Allow manual overrides (resource substitutions, pricing adjustments)
  - Trigger actions based on page updates (e.g., status change)

**Inputs:** Agent outputs, project state, validation results, user comments
**Outputs:** Notion pages/databases, activity logs, user feedback to agents
**Tools:** Notion API (via MCP when available)
**Provider:** Gemini Flash (simple page updates) or Claude (complex page structuring)

---

### PowerPoint Agent
**Purpose:** Generate professional proposal presentations using Claude's document creation skills

**Responsibilities:**
- **Document Generation:**
  - Use Claude's PPTX skill to create presentations
  - Follow firm templates and brand guidelines
  - Import content from approved proposal outline
  - Select appropriate slide layouts for each section
  - Generate charts and visualizations (timeline, team structure, pricing)
  
- **Asset Management:**
  - Access digital asset library (logos, photos, icons, case study visuals)
  - Insert relevant case study slides
  - Include team member photos and bios
  - Add methodology diagrams and process flows
  
- **Formatting:**
  - Apply consistent styling across slides
  - Ensure proper hierarchy (titles, bullets, emphasis)
  - Balance text density (not too crowded)
  - Use visual elements appropriately (not overdesigned)
  - Maintain accessibility standards
  
- **Iteration:**
  - Accept feedback from project lead
  - Make revisions efficiently
  - Track version history
  - Regenerate sections without affecting entire deck
  
- **Delivery:**
  - Export final PowerPoint file
  - Send to Email Agent for delivery to client
  - Upload to Notion via Notion Agent
  - Store in document repository

**Inputs:** Approved proposal outline, templates, asset library, feedback
**Outputs:** PowerPoint file, revision notes
**Tools:** Claude's PPTX skill, asset library, template library
**Provider:** Claude Sonnet (exclusive - uses Claude-specific skills)

---

## Core Infrastructure

### Database Layer (PostgreSQL + pgvector)

**Resources Table:**
- Stores people, vendors, tools, services
- Flexible JSONB attributes for capabilities, pricing, availability
- Confidence scores and validation timestamps
- Generated search text for full-text search

**Resource Embeddings Table:**
- Vector embeddings for semantic search
- One embedding per resource
- Regenerated when resource attributes change

**Documents Table:**
- Full-text storage of proposals, resumes, case studies, bios
- Metadata (client, year, methodologies, outcomes)
- Links to related resources and projects
- Generated search vectors for full-text search

**Document Embeddings Table:**
- Vector embeddings for semantic document search
- Separate from documents for performance

**Validations Table:**
- Tracks validation workflow state
- Links to resources and attribute paths
- Email thread tracking
- Status, priority, timeout management
- Results storage (flexible JSONB)

**Projects Table:**
- Overall project state machine
- Status (received → analyzing → validating → planning → draft_ready → sent → won/lost)
- Lock management for concurrency control
- Timeout tracking
- Metadata and state data (JSONB)

**Project Tasks Table:**
- Granular tasks within projects
- Dependencies and blocking relationships
- Retry logic and scheduling
- Results and error tracking

**State Transitions Log:**
- Audit trail of all state changes
- Reasoning for transitions
- User actions vs. automatic transitions

### State Management (PostgreSQL + Redis + Celery)

**PostgreSQL (Durable State):**
- Source of truth for all entities and workflow state
- Survives system restarts
- Queryable for reporting and analytics
- ACID transactions for consistency

**Redis (Active Work Coordination):**
- Project locks (prevent duplicate work, TTL-based)
- Work queues by priority (high/medium/low)
- Email deduplication (don't send same email twice within 48 hours)
- Email thread tracking (fast lookup for responses)
- Active project state (currently processing)
- Cache for frequently accessed data

**Celery (Task Orchestration):**
- Async task execution (email sending, validation execution)
- Scheduled tasks (check emails every 60 seconds, process work queue every 2 minutes)
- Retry logic (exponential backoff for transient failures)
- Timeout handling (validation timeouts, stuck analysis)
- Distributed execution (can scale to multiple workers)
- Task dependencies and chaining

### Email Infrastructure

**SMTP (Sending):**
- Dedicated email account or user's email (via OAuth)
- Email templates with variable substitution
- Thread tracking via message IDs
- Signature and branding

**IMAP (Receiving):**
- Background task checking inbox every 60 seconds
- Thread matching via In-Reply-To and References headers
- Message parsing and structured extraction
- Attachment handling

**Thread Management:**
- Store thread IDs in Redis for fast lookup
- Associate threads with validation tasks or projects
- Timeout tracking per thread
- Response detection and routing

### Notion Integration

**Databases:**
- RFP Tracking (one page per RFP with analysis)
- Project Plans (one page per project with phase database)
- Resources (availability, capabilities, utilization)
- Opportunities (pipeline tracking)
- Activity Feed (event log)

**API Usage:**
- Create pages with structured properties
- Update page content and properties
- Query databases with filters
- Listen for comments and page updates
- Generate inline databases for sub-entities

**MCP Integration:**
- Use Notion MCP when available for richer interactions
- Fallback to direct API for core functionality

### Web Research

**Google Search, Gemini with Grounding:**
- Semantic search for external consultants
- Company/client research
- Market information gathering

**Web Fetching:**
- Direct HTTP requests to fetch pages
- BeautifulSoup for HTML parsing
- LinkedIn profile scraping (careful/respectful crawling)
- Vendor website information extraction

**Rate Limiting:**
- Implement delays between requests
- Cache fetched pages (24 hour TTL)
- Fallback when rate limited

---

## Design Principles

### 1. Simplicity First
- Flat schemas over complex normalization where possible
- JSONB for flexibility rather than rigid tables
- One embedding per entity, not multiple types
- Straightforward state machines, not elaborate DAGs
- Start simple, add complexity only when proven necessary

### 2. AI-Driven Decision Making
- Teach agents principles and examples, not hardcoded rules
- Let agents decide when to validate based on confidence and criticality
- Allow agents to compose emails contextually, not from rigid templates
- Enable agents to infer capabilities and learn patterns
- Rely on LLM judgment rather than exhaustive conditionals
- **Example:** Don't code "if confidence < 70 then validate" - instead, teach agent "validate uncertain information that matters for this project"

### 3. Tool Infrastructure Without Business Logic
- Tools execute actions, agents decide when/why
- Clean separation: tools are dumb, agents are smart
- Standardized interfaces (BaseTool, ToolResult)
- Tools have no dependencies on each other
- Easy to test in isolation

### 4. Provider Strategy
- **Default to Gemini Flash** for speed and cost
  - Email parsing and composition
  - Simple data extraction
  - KB updates
  - Notion page updates
  - Classification tasks
  
- **Use Claude Sonnet** when needed for quality
  - Complex reasoning (RFP analysis, planning)
  - Judgment calls (validation decisions, resource substitutions)
  - Document generation (PowerPoint via skills)
  - Multi-step problem solving
  
- **Provider selection per task**, not per agent
- Track costs and optimize over time

### 5. Native SDKs Over Frameworks
- Use Anthropic and Google SDKs directly
- Thin wrapper for multi-provider support
- No heavy frameworks (LangChain, CrewAI, etc.)
- Full access to provider-specific features (Claude skills, Gemini speed)
- Simple debugging and troubleshooting

### 6. State Management Strategy
- **PostgreSQL = source of truth** (durable, queryable)
- **Redis = coordination layer** (locks, queues, fast lookups)
- **Celery = task scheduler** (retries, timeouts, distribution)
- Clear checkpointing after major steps
- Idempotent operations where possible
- Recovery from restarts without data loss

---

## Workflow State Machine

```
RFP Received
  ↓
[Orchestrator assigns to Brief Review Agent]
  ↓
Analyzing (Brief Review Agent)
  ↓
  ├→ Needs Clarification → Email Agent sends questions → Awaiting Clarification
  │                            ↓
  │                       [Response received or timeout]
  │                            ↓
  └────────────────────────────┘
  ↓
Requirements Ready
  ↓
[Orchestrator assigns to Planning Agent]
  ↓
Validating (Planning Agent identifies needs)
  ↓
  [Concurrent validation tasks via Email Agent]
  ↓
  [Wait for responses, handle timeouts]
  ↓
  [Update KB via Knowledge Agent]
  ↓
Planning (Planning Agent generates plan)
  ↓
  ├→ Design Questions → Email to Project Lead → Awaiting Decisions
  │                         ↓
  │                    [Feedback received]
  │                         ↓
  └─────────────────────────┘
  ↓
Draft Planning Complete
  ↓
[Orchestrator assigns to Go to Market Agent]
  ↓
Proposal Outlining
  ↓
  ├→ Needs Revision → [Agent revises] → Proposal Outlining
  │                         ↓
  └─────────────────────────┘
  ↓
Ready for Review
  ↓
[Project Lead reviews in Notion, provides feedback]
  ↓
  ├→ Revision Requested → [Agents iterate] → Ready for Review
  │                             ↓
  └─────────────────────────────┘
  ↓
Approved
  ↓
[Orchestrator assigns to PowerPoint Agent]
  ↓
Generating Presentation
  ↓
  ├→ Feedback → [PowerPoint Agent revises] → Generating Presentation
  │                  ↓
  └──────────────────┘
  ↓
Final Proposal Ready
  ↓
[Email Agent sends to client]
[Notion Agent updates opportunity]
[Files saved to repository]
  ↓
Proposal Sent
  ↓
[Await client decision]
  ↓
Won / Lost / No Response
```

---

## Timeout & Escalation Policies

**Email Response Timeouts:**
- Client clarifications: 72 hours → Proceed without or escalate
- Resource validations: 72 hours → Try alternative method (web research) or proceed with caveat
- Project lead design decisions: 48 hours → Escalate to human

**Processing Timeouts:**
- RFP analysis: 1 hour → Escalate (likely stuck)
- Project planning: 2 hours → Escalate
- Proposal generation: 1 hour → Escalate

**Recheck Intervals:**
- Projects in validating state: Check every 5 minutes for new responses
- Projects awaiting clarification: Check every 1 hour
- Blocked projects: Check every 30 minutes for resolution

**Escalation Actions:**
- Send notification to project lead via email
- Update Notion page with blocker details
- Mark project as "blocked" in database
- Add to high-priority queue for human review

---

## Concurrency & Safety

**Distributed Locks:**
- Acquire lock before working on project (5 minute TTL)
- Renew lock every 60 seconds while working
- Release lock when done
- Automatic cleanup of stale locks every 5 minutes

**Deduplication:**
- Don't send same email to same person about same attribute within 48 hours
- Check Redis before sending validation emails
- Mark email sent with TTL

**Idempotency:**
- Operations safe to retry (check before act)
- Validation tasks track status (don't resend if already sent)
- KB updates use upsert logic

**Concurrent Validations:**
- Multiple validation tasks run in parallel via Celery
- Each validation independent
- Results aggregated when all complete or timeout

---

## Error Handling & Resilience

**Retry Logic:**
- Email sending: 3 retries with exponential backoff
- Web requests: 3 retries with 1s, 5s, 15s delays
- KB queries: Immediate retry once, then fail
- LLM calls: Retry on rate limits, fail on other errors

**Partial Failures:**
- Some validations succeed, some fail → Proceed with caveats if non-critical failed
- Critical validation fails → Block project and escalate
- Log all failures for analysis

**System Restart Recovery:**
- Scan for projects with expired locks on startup
- Release locks and re-queue projects
- Resume from last checkpoint
- Celery auto-retries in-flight tasks

**Data Consistency:**
- PostgreSQL transactions for related updates
- Redis operations use Lua scripts for atomicity
- Validate data before writing
- Maintain audit trail of all changes

---

## Security & Privacy

**Data Protection:**
- Database encryption at rest
- TLS for all network communication
- Environment variables for credentials (never in code)
- OAuth for email when possible
- Notion/API connections use tokens

**Access Control:**
- Agent-level permissions (which agents can access what)
- Human approval required for:
  - Sending emails to clients
  - Major KB changes (pricing, capabilities)
  - Final proposal delivery
- Audit trail of all actions

**Sensitive Data:**
- Client RFP content (potentially confidential)
- Internal pricing and costs
- Team member contact information
- Vendor pricing
- Project outcomes



---

## Monitoring & Observability

**Metrics to Track:**
- Project state distribution (how many in each status)
- Work queue depth by priority
- Validation response rates and times
- Email send/receive success rates
- LLM API usage and costs by provider
- Lock acquisition success/failure
- State transition counts and timing
- Agent execution times

**Logging:**
- All agent decisions and reasoning
- Tool calls and results
- State transitions with context
- Errors and exceptions with stack traces
- Performance timing for operations

**Alerts:**
- Projects stuck in state > threshold time
- High rate of validation timeouts
- LLM API errors or rate limits
- Email delivery failures
- Lock cleanup frequency increasing (indicates crashes)
- High cost burn rate

**Dashboards:**
- Project pipeline view (count by stage)
- Active work queue (what's being processed)
- Validation status board (pending/completed/timed out)
- Cost tracking by provider and task type
- Resource utilization heatmap

Use Arize Pheonix for traceability

---

## Success Metrics

**Efficiency:**
- Time to first draft: < 3 hours (vs. days currently)
- Proposal quality score: Maintained or improved
- Validation response rate: > 70%
- Client clarification cycle time: < 24 hours

**Accuracy:**
- KB data accuracy: > 90% on validated attributes
- Resource allocation accuracy: > 85% (right person for the job)
- Pricing accuracy: Within 10% of actual costs
- Timeline accuracy: Within 15% of actual duration

**Business Impact:**
- Proposal volume: 3x increase in capacity
- Win rate: Maintained or improved
- Resource utilization: Better allocation, less idle time
- Sales team satisfaction: Can handle more opportunities

**System Health:**
- Uptime: > 99%
- Mean time to recovery: < 15 minutes
- Error rate: < 2% of operations
- Cost per proposal: < $2 (LLM API costs)

---

## Open Decisions

**1. Email Authentication:**
- Option A: Dedicated system email (assistant@firm.com) - simpler, less personal
- Option B: Send from user's email via OAuth - more personal, complex auth
- **Recommendation:** Start with A, migrate to B if response rates suffer - CONFIRMED

**2. Initial Knowledge Base Population:**
- Option A: Start empty, learn from usage - no upfront work, slow start
- Option B: Bulk import existing data - immediately useful, data quality issues
- **Recommendation:** B - Seed with current team roster and past proposals - CONFIRMED, Add means of doing this via Notion

**3. Agent Autonomy Level:**
- Option A: High autonomy (send emails without approval) - faster, riskier
- Option B: Human approval for external comms - safer, slower
- **Recommendation:** B for Phase 1, increase autonomy as trust builds - CONFIRMED

**4. Vector Search Provider:**
- Option A: pgvector (simpler architecture, lower cost)
- Option B: Pinecone (specialized, faster at scale)
- **Recommendation:** A - Start with pgvector, migrate only if performance issues - CONFIRMED

**5. Workflow Engine:**
- Option A: Custom Celery implementation (maximum control)
- Option B: Temporal.io (managed workflows, better observability)
- **Recommendation:** A for MVP, consider B if workflow complexity grows significantly -CONFIRMED

---

## Cost Estimate

**Monthly Operating Costs (10 proposals/month):**
- Hosting (Railway/Fly.io): $30
- PostgreSQL (managed): $30
- Redis: $10
- LLM APIs: $50-150 (depends on provider mix)
- Brave Search: $0 (free tier sufficient)
- Email: $0 (existing provider)
- Notion: $0 (API free)
- **Total: $120-220/month**

**Development Cost:**
- 8 weeks × 40 hours = 320 hours
- At $100/hour = $32,000 (if outsourced)
- Or solo development over 8-10 weeks

**Break-even:**
- At $1,500/month SaaS price
- Need 1 customer for break-even
- 10 customers = $180K ARR

---

## Technology Stack Summary

**Backend:**
- Python 3.11+
- FastAPI (API server)
- SQLAlchemy (ORM)
- Celery (task queue)
- Redis (coordination)
- PostgreSQL + pgvector (database)

**LLM Providers:**
- Google Gemini (primary - speed/cost)
- Anthropic Claude (secondary - quality/skills)

**Integrations:**
- SMTP/IMAP (email)
- Notion API
- Google Search API
- Gemini (embeddings only)

**Deployment:**
- Docker containers
- Railway, Fly.io, or Render
- Managed PostgreSQL (Supabase/Render)
- Managed Redis

**Monitoring:**
- Sentry (error tracking)
- Prometheus (metrics)
- Custom dashboards

---
