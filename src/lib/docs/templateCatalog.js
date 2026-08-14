/** Canonical template documentation — single source for /docs UI */

export const DOC_CATEGORIES = [
  { id: "onboarding", label: "Getting Started", desc: "Full onboarding & FAQs", borderAnim: "stitch", innerAnim: "matrix" },
  { id: "workflows", label: "Workflows", desc: "13 pipeline starters", borderAnim: "march", innerAnim: "grid" },
  { id: "digests", label: "Digests", desc: "Scheduled delivery", borderAnim: "shimmer", innerAnim: "nodes" },
  { id: "prompts", label: "Apps & prompts", desc: "Assistant presets", borderAnim: "pulse", innerAnim: "wave" },
  { id: "nodes", label: "Node reference", desc: "How pieces connect", borderAnim: "trace", innerAnim: "spark" },
  { id: "deployment", label: "Cloud Deployment", desc: "Vercel, Render & URLs", borderAnim: "beam", innerAnim: "orbit" },
];

export const NODE_TYPES = [
  {
    id: "trigger",
    label: "Trigger",
    role: "Entry point — user input, schedule, or webhook payload.",
    outputs: ["input text", "metadata (chat_id, etc.)"],
    config: ["Label", "Optional webhook input mapping"],
  },
  {
    id: "retrieve",
    label: "Retrieve",
    role: "Semantic + BM25 search over a knowledge base.",
    outputs: ["ranked chunks", "citations for downstream LLM"],
    config: ["knowledge_id (required)", "limit (default 6–8)", "cross-KB RRF when multiple"],
  },
  {
    id: "llm",
    label: "LLM",
    role: "Calls workspace model with prompt + prior node context.",
    outputs: ["generated text", "parsed subject lines for digests"],
    config: ["System/user prompt", "Model from Settings → Providers", "Temperature via provider"],
  },
  {
    id: "transform",
    label: "Transform",
    role: "Mustache-style template on {{input}} / {{output}}.",
    outputs: ["formatted string"],
    config: ["template string with {{input}}, {{output}}, {{item}}"],
  },
  {
    id: "agent",
    label: "Agent",
    role: "Multi-tool agent loop (summarize, kb_search, calculator, etc.).",
    outputs: ["final answer + tool receipts"],
    config: ["tools[]", "agent prompt", "optional knowledge_id for kb_search"],
  },
  {
    id: "human",
    label: "Human review",
    role: "Pauses run until approval in Runs / pending queue.",
    outputs: ["approved text continues pipeline"],
    config: ["message template", "require_approval flag"],
  },
  {
    id: "loop",
    label: "Loop",
    role: "Splits input by lines; runs prompt per item (concurrency configurable).",
    outputs: ["aggregated results"],
    config: ["max items", "per-item prompt with {{item}}", "concurrency"],
  },
  {
    id: "notify",
    label: "Notify",
    role: "Delivers via email, Slack, Discord, Telegram, or webhook.",
    outputs: ["delivery status"],
    config: ["channel", "to / chat_id / webhook URL", "subject", "message templates"],
  },
  {
    id: "jira",
    label: "Jira",
    role: "Creates or updates Jira issues via integration.",
    outputs: ["issue key / URL"],
    config: ["project_key", "issue_type", "summary/description from {{output}}"],
  },
  {
    id: "github",
    label: "GitHub",
    role: "Creates GitHub issues in a configured repo.",
    outputs: ["issue number / URL"],
    config: ["repo", "title/body templates", "labels"],
  },
  {
    id: "linear",
    label: "Linear",
    role: "Creates Linear issues in a team.",
    outputs: ["issue id / URL"],
    config: ["team_id", "title/description from templates"],
  },
  {
    id: "output",
    label: "Output",
    role: "Terminal node — result stored on the run record.",
    outputs: ["visible in /runs inspector"],
    config: ["label only"],
  },
];

const wf = (id, name, desc, tagline, nodes, configure, integrations = [], tips = [], link = "/workflows") => ({
  id,
  category: "workflows",
  name,
  desc,
  tagline,
  nodes,
  configure,
  integrations,
  tips,
  links: [{ href: link, label: "Open workflows" }, { href: "/runs", label: "View runs" }],
});

export const TEMPLATE_DOCS = [
  {
    id: "getting-started",
    category: "onboarding",
    name: "NovaFlow AI 101 Onboarding",
    desc: "A brief tour of NovaFlow platforms & basic terms.",
    tagline: "Learn how Workspaces, Apps, and Workflows interact.",
    nodes: ["workspace", "apps", "workflow", "runs"],
    configure: [
      { title: "Workspace Concept", detail: "A workspace isolates users, workflows, keys, and knowledge bases. Everything you build belongs to your active workspace." },
      { title: "Apps vs Solutions", detail: "Apps are user-facing portals. The AI Operating System automatically composes background solutions configured with capabilities to solve tasks." },
      { title: "Workflows", detail: "Workflows are visual pipelines of nodes (Trigger → Retrieve → LLM → Notify). They automate repetitive tasks via API or cron schedules." }
    ],
    integrations: ["Active Account", "Workspace Access"],
    tips: [
      "Switch workspaces using the workspace dropdown in the top-right header.",
      "Check /developer to test backend routes interactively."
    ],
    links: [{ href: "/dashboard", label: "Go to Dashboard" }]
  },
  {
    id: "team-invite",
    category: "onboarding",
    name: "Managing Teams & SMTP Invites",
    desc: "How to invite team members and configure SMTP settings.",
    tagline: "Learn how workspace tenancy, roles, and SMTP email invites operate.",
    nodes: ["admin", "settings", "smtp", "roles"],
    configure: [
      { title: "SMTP Configuration", detail: "SMTP details are verified for your-smtp@example.com with custom app passwords. Invites are fully formatted to bypass spam filters.", href: "/settings" },
      { title: "Sending Invites", detail: "Go to Admin Settings → Teams & Roles → Invite Member. Enter their email and select a role (viewer, editor, admin).", href: "/settings" },
      { title: "Roles Hierarchy", detail: "viewer (read-only), editor (create/delete workflows & apps), admin (full workspace control), super_admin (manages entire platform)." },
      { title: "Accepting Invites", detail: "The recipient clicks the link in their email. If they are new, they register. Upon logging in, they automatically join the workspace." }
    ],
    integrations: ["Gmail SMTP Provider", "User Database"],
    tips: [
      "If the recipient doesn't see the email, ask them to check their spam box.",
      "Ensure the email template contains correct absolute domain URLs for registration."
    ],
    links: [{ href: "/settings", label: "Admin Settings" }]
  },
  {
    id: "knowledge-base",
    category: "onboarding",
    name: "Grounded RAG & Knowledge Bases",
    desc: "How to upload documents and query vector storage.",
    tagline: "Everything about text parsing, embeddings, and RAG pipelines.",
    nodes: ["upload", "chunking", "vector", "citations"],
    configure: [
      { title: "File Uploading", detail: "Go to Knowledge → upload documents (PDF, DOCX, TXT, CSV, JSON). Supported by high-speed concurrent chunked upload for files up to 100GB+.", href: "/knowledge" },
      { title: "Chunking & Vectorizing", detail: "NovaFlow splits documents into 1000-character chunks with 100-character overlap, creates embeddings, and writes to Milvus." },
      { title: "Retrieval RAG Node", detail: "In a workflow, add a Retrieve node. Specify the Knowledge Base ID to retrieve grounded reference chunks at runtime.", href: "/workflows" },
      { title: "Verifying Answers", detail: "Go to the Q&A Preview inside the Knowledge Base to search indexed chunks semantic-search style.", href: "/knowledge" }
    ],
    integrations: ["Milvus Vector Store", "Embedding Models (OpenAI/Ollama)"],
    tips: [
      "Large files are uploaded in parallel 8MB chunks to keep RAM usage under 8MB.",
      "Use clean formatted PDFs to ensure highly accurate text parsing."
    ],
    links: [{ href: "/knowledge", label: "Explore Knowledge" }]
  },
  {
    id: "model-lab",
    category: "onboarding",
    name: "Model Lab & Fine-tuning",
    desc: "Train custom models and compare performance.",
    tagline: "Import training data, estimate costs, train and test models.",
    nodes: ["import", "estimate", "train", "eval"],
    configure: [
      { title: "Importing Dataset", detail: "Go to Model Lab → Datasets → Create Dataset. Import CSV or JSON Lines data formatted with user/assistant prompts.", href: "/model-lab" },
      { title: "Cost Estimation", detail: "Before training, click 'Estimate Cost' to view calculated token expenses based on base models (e.g. gpt-4o-mini).", href: "/model-lab" },
      { title: "Fine-tune Job", detail: "Click 'Start Training'. Monitor logs and status from the jobs table. Training is executed asynchronously.", href: "/model-lab" },
      { title: "Evaluation Suites", detail: "Run automated evaluations comparing your fine-tuned model against baseline models using test datasets.", href: "/evaluation" }
    ],
    integrations: ["Model Provider API", "Evaluation Datasets"],
    tips: [
      "Always start with at least 50 high-quality prompt-reply pairs for training.",
      "Use A/B model routing to split user traffic between models in production."
    ],
    links: [{ href: "/model-lab", label: "Open Model Lab" }]
  },
  {
    id: "integrations-webhook",
    category: "onboarding",
    name: "Incoming Webhooks & Integrations",
    desc: "How to trigger workflows from external services.",
    tagline: "Connect GitHub, Jira, Slack, Discord, and Telegram webhooks.",
    nodes: ["webhook", "trigger", "notify", "channel"],
    configure: [
      { title: "Webhook Trigger", detail: "Set a workflow's trigger node to webhook. Copy the unique POST webhook URL from the workflow builder.", href: "/workflows" },
      { title: "Mapping Inputs", detail: "External services POST JSON data. Map the parameters using transform nodes (e.g. {{input.body.message}}).", href: "/workflows" },
      { title: "Slack / Discord webhook", detail: "Paste Slack/Discord channel webhooks inside the integration settings panel.", href: "/settings" },
      { title: "Telegram bot setup", detail: "@BotFather bot token linked to a Notify node with Telegram destination.", href: "/settings" }
    ],
    integrations: ["Slack Webhook", "Telegram Bot API", "Jira/GitHub credentials"],
    tips: [
      "Test Webhook payload format using standard curl or Postman before deploying.",
      "Check Runs history to inspect raw webhook request and response values."
    ],
    links: [{ href: "/developer", label: "API Docs" }]
  },
  {
    id: "faq-troubleshoot",
    category: "onboarding",
    name: "Troubleshooting & FAQs",
    desc: "Quick fixes for common setup and runtime errors.",
    tagline: "Read FAQs about email deliverability, vector stores, and model keys.",
    nodes: ["errors", "logs", "fixes", "status"],
    configure: [
      { title: "Why don't I get email invites?", detail: "Verify the sender SMTP configurations in config.py. Check your junk/spam folder for messages from your-smtp@example.com." },
      { title: "Why does the UI show 'Connecting' forever?", detail: "Ensure both backend API and Docker redis containers are running. Check Redis health using `docker compose ps`." },
      { title: "How do I fix vector indexing errors?", detail: "Ensure the Milvus container is online. Verify that the documents are text-extractable (not scanned images without OCR)." },
      { title: "Where are application logs stored?", detail: "Backend logs print to stdout inside the Docker container. Check them using `docker compose logs api`." }
    ],
    integrations: ["Docker Compose", "Health Endpoints"],
    tips: [
      "Use /health API endpoint to verify backend sub-service health states.",
      "Ensure API key header is formatted as 'Authorization: Bearer <token>'."
    ],
    links: [{ href: "/developer", label: "System Diagnostics" }]
  },
  wf(
    "rag",
    "RAG Q&A pipeline",
    "Retrieve docs then answer with LLM",
    "Ground every answer in your knowledge base with citations.",
    ["trigger", "retrieve", "llm", "output"],
    [
      { title: "Create a knowledge base", detail: "Upload PDFs, docs, or paste text at /knowledge. Wait for indexing to complete.", href: "/knowledge" },
      { title: "New workflow from template", detail: "Workflows → Create → pick RAG Q&A. Name your pipeline.", href: "/workflows" },
      { title: "Bind retrieve node", detail: "Open builder → Retrieve node → set knowledge_id to your library.", href: "/workflows" },
      { title: "Tune LLM prompt", detail: "Default prompt asks for Direct answer · Bullets · [n] citations. Edit for your tone.", href: "/workflows" },
      { title: "Publish & run", detail: "Set status Published. Run from builder or POST /workflow/run with input text.", href: "/developer" },
    ],
    ["OpenAI or compatible provider in Settings", "Indexed knowledge base"],
    ["Link assistant apps to same KB for chat parity.", "Increase retrieve limit for long docs.", "Use Evaluation suites to regression-test answers."]
  ),
  wf(
    "support",
    "Support triage",
    "Classify and draft support replies",
    "Turn raw tickets into classified replies + internal notes.",
    ["trigger", "llm", "output"],
    [
      { title: "Create from template", detail: "No retrieve node — paste ticket text as workflow input.", href: "/workflows" },
      { title: "Optional: attach KB", detail: "Add a retrieve node before LLM if you want policy-aware replies.", href: "/workflows" },
      { title: "Customize classification", detail: "LLM prompt outputs P1–P4 priority, category, sentiment, customer reply, internal notes.", href: "/workflows" },
      { title: "Automate intake", detail: "Trigger via API webhook or Zapier using POST /workflow/run.", href: "/developer" },
    ],
    ["LLM provider"],
    ["Pipe output to Slack alert template for team visibility.", "Test solution execution paths directly in /chat."]
  ),
  wf(
    "research",
    "Research brief",
    "Retrieve sources and synthesize a brief",
    "Executive summary, findings, implications, and gaps from your docs.",
    ["trigger", "retrieve", "llm", "output"],
    [
      { title: "Index research corpus", detail: "Load reports, wikis, and notes into a dedicated knowledge base.", href: "/knowledge" },
      { title: "Set retrieve limit to 8", detail: "Template defaults to broader context than RAG Q&A.", href: "/workflows" },
      { title: "Topic as input", detail: "Run with a research question; LLM structures Executive summary · Key findings · Implications · Gaps.", href: "/workflows" },
    ],
    ["Knowledge base", "LLM provider"],
    ["Schedule weekly briefs via Digests using daily_digest template.", "Export run JSON from /runs for archiving."]
  ),
  wf(
    "enrich",
    "Transform + LLM",
    "Format input with a template then run LLM",
    "Pre-process raw text with {{input}} templates before the model.",
    ["trigger", "transform", "llm", "output"],
    [
      { title: "Edit transform template", detail: "Default: 'User message:\\n{{input}}\\n\\nRespond helpfully.' Use {{input}} and {{output}} placeholders.", href: "/workflows" },
      { title: "Chain to LLM", detail: "Transform output becomes LLM context automatically via graph edges.", href: "/workflows" },
      { title: "Use for formatting", detail: "Normalize emails, JSON, or CSV snippets before summarization.", href: "/workflows" },
    ],
    ["LLM provider"],
    ["Insert multiple transform nodes for multi-step formatting."]
  ),
  wf(
    "agent_loop",
    "Agent + review",
    "Tool agent with human review gate",
    "Agent uses tools, then human approves before final output.",
    ["trigger", "agent", "human", "output"],
    [
      { title: "Select tools", detail: "Default: summarize + kb_search. Add calculator, translate_en in builder.", href: "/chat" },
      { title: "Agent prompt", detail: "Instructs Summary · Details · Confidence format.", href: "/workflows" },
      { title: "Human gate", detail: "Run pauses at human node — approve in Runs or pending runs API.", href: "/runs" },
      { title: "Knowledge for kb_search", detail: "Set knowledge_id on agent node or link workspace KB.", href: "/knowledge" },
    ],
    ["LLM provider", "Optional knowledge base"],
    ["Test capabilities first in Chat before publishing workflow.", "require_approval=true blocks until explicit approve."]
  ),
  wf(
    "batch",
    "Batch loop",
    "Process each line of input in parallel tasks",
    "One input line per loop iteration with configurable concurrency.",
    ["trigger", "loop", "output"],
    [
      { title: "Paste multi-line input", detail: "Each line becomes {{item}} in the loop prompt.", href: "/workflows" },
      { title: "Set max items", detail: "Default max 5 — raise carefully for cost/latency.", href: "/workflows" },
      { title: "Concurrency", detail: "Loop node supports parallel item processing (see builder inspector).", href: "/workflows" },
      { title: "Per-item prompt", detail: "Template: RESULT: <outcome> | WHY: <reason>\\nItem: {{item}}", href: "/workflows" },
    ],
    ["LLM provider"],
    ["Great for bulk classification, tagging, or QA rows for Model Lab."]
  ),
  wf(
    "telegram_qa",
    "Telegram Q&A bot",
    "Answer questions and reply via Telegram",
    "LLM reply delivered to Telegram chat via notify node.",
    ["trigger", "llm", "notify", "output"],
    [
      { title: "Telegram bot token", detail: "Settings → Integrations → Telegram. Paste bot token from @BotFather.", href: "/settings" },
      { title: "Register webhook", detail: "Use integrations API or Settings to register webhook URL.", href: "/developer" },
      { title: "notify node", detail: "channel=telegram, to={{chat_id}}, message={{output}}", href: "/workflows" },
      { title: "Trigger payload", detail: "Pass chat_id in input JSON when testing manually.", href: "/developer" },
    ],
    ["Telegram bot token", "LLM provider"],
    ["Keep replies under 800 chars — prompt enforces this.", "Test with integrations/notify/test preset in Developer."]
  ),
  wf(
    "daily_digest",
    "Daily digest email",
    "Retrieve knowledge and email a summary",
    "Highlights, risks, asks — with parsed email subject line.",
    ["trigger", "retrieve", "llm", "notify", "output"],
    [
      { title: "Knowledge source", detail: "Retrieve node needs knowledge_id — pick team wiki or ops notes.", href: "/knowledge" },
      { title: "LLM subject line", detail: "First line must be 'Subject: …' — workflow extracts {{subject}} for notify.", href: "/workflows" },
      { title: "Email notify", detail: "channel=email, to=team@…, subject={{subject}}, message={{output}}", href: "/settings" },
      { title: "Schedule", detail: "Use /digests UI or POST /workflow/schedules with cron.", href: "/digests" },
      { title: "SMTP / provider", detail: "Configure email integration in Settings if not using defaults.", href: "/settings" },
    ],
    ["Knowledge base", "Email integration", "LLM provider"],
    ["Digests hub wraps this template with Gmail/Slack/Discord/Telegram variants.", "Cron example: 0 9 * * * for 9am UTC daily."]
  ),
  wf(
    "slack_alert",
    "Slack alert",
    "Summarize input and post to Slack",
    "What happened · Impact · Action format under 500 chars.",
    ["trigger", "llm", "notify", "output"],
    [
      { title: "Slack webhook", detail: "Settings → Integrations → Slack incoming webhook URL.", href: "/settings" },
      { title: "notify override", detail: "Leave to empty to use Settings default; or paste channel webhook in node.", href: "/workflows" },
      { title: "Test delivery", detail: "Developer → Test Slack notify preset.", href: "/developer" },
    ],
    ["Slack webhook URL", "LLM provider"],
    ["Chain after eval runs for regression alerts.", "Use with batch template output as input."]
  ),
  wf(
    "discord_alert",
    "Discord alert",
    "Summarize input and post to Discord",
    "Short Discord-formatted alert via webhook.",
    ["trigger", "llm", "notify", "output"],
    [
      { title: "Discord webhook", detail: "Settings → Integrations → Discord webhook URL.", href: "/settings" },
      { title: "notify node", detail: "channel=discord, message={{output}}", href: "/workflows" },
      { title: "Test", detail: "Developer → Test Discord notify.", href: "/developer" },
    ],
    ["Discord webhook", "LLM provider"],
    ["Bold sparingly — prompt limits to 400 characters."]
  ),
  wf(
    "jira_ticket",
    "Jira ticket from input",
    "Create a Jira issue from workflow output",
    "LLM formats TITLE + DESCRIPTION, Jira node creates issue.",
    ["trigger", "llm", "jira", "output"],
    [
      { title: "Jira integration", detail: "Settings → Integrations → Jira site URL + API token.", href: "/settings" },
      { title: "jira node", detail: "project_key (e.g. NF), issue_type, summary={{output}}, description={{input}}", href: "/workflows" },
      { title: "LLM output shape", detail: "Must output TITLE: line and DESCRIPTION block for parsing.", href: "/workflows" },
      { title: "Verify", detail: "Developer → Verify Jira preset.", href: "/developer" },
    ],
    ["Jira Cloud API token", "LLM provider"],
    ["set_output=true stores issue key on run record."]
  ),
  wf(
    "github_issue",
    "GitHub issue from input",
    "Create a GitHub issue from workflow output",
    "Structured TITLE/BODY for GitHub issues API.",
    ["trigger", "llm", "github", "output"],
    [
      { title: "GitHub token", detail: "Settings → Integrations → PAT with repo scope.", href: "/settings" },
      { title: "github node", detail: "repo owner/name, title={{output}}, body={{input}}, labels", href: "/workflows" },
      { title: "Verify GitHub", detail: "Developer → Verify GitHub preset.", href: "/developer" },
    ],
    ["GitHub PAT", "LLM provider"],
    ["Default labels=bug — change in node data."]
  ),
  wf(
    "linear_issue",
    "Linear issue from input",
    "Create a Linear issue from workflow output",
    "Linear node creates issue from LLM-structured title/description.",
    ["trigger", "llm", "linear", "output"],
    [
      { title: "Linear API key", detail: "Settings → Integrations → Linear.", href: "/settings" },
      { title: "team_id", detail: "Set on linear node — find in Linear team settings.", href: "/workflows" },
      { title: "Verify Linear", detail: "Developer → Verify Linear preset.", href: "/developer" },
    ],
    ["Linear API key", "LLM provider"],
    ["Great for product intake from Slack messages via transform."]
  ),
  // Digests (wrap daily_digest)
  {
    id: "digest_gmail",
    category: "digests",
    name: "Daily team email",
    desc: "Morning standup brief via Gmail",
    tagline: "Digests hub → daily_digest workflow → email notify.",
    nodes: ["trigger", "retrieve", "llm", "notify", "output"],
    configure: [
      { title: "Open Digests", detail: "Pick Daily team email template card.", href: "/digests" },
      { title: "Select knowledge base", detail: "Step 2 — choose KB for grounded highlights/risks/asks.", href: "/digests" },
      { title: "Recipient email", detail: "Step 3 — team@company.com or distribution list.", href: "/digests" },
      { title: "Subject template", detail: "Default {{subject}} — parsed from LLM first line.", href: "/digests" },
      { title: "Cron schedule", detail: "Step 4 — e.g. 0 9 * * * weekdays standup.", href: "/digests" },
      { title: "Auto-publish", detail: "Creates workflow, patches notify node, publishes, schedules.", href: "/digests" },
    ],
    integrations: ["Knowledge base", "Email/Gmail SMTP", "LLM provider"],
    tips: ["Edit graph after create in workflow builder.", "Pause schedule from Digests or /workflow/schedules."],
    links: [{ href: "/digests", label: "Digests hub" }, { href: "/workflows", label: "Workflows" }],
  },
  {
    id: "digest_incidents",
    category: "digests",
    name: "Incidents digest",
    desc: "On-call risk briefing email",
    tagline: "Prefixed subject for inbox filters — Incidents & risks — …",
    nodes: ["trigger", "retrieve", "llm", "notify", "output"],
    configure: [
      { title: "Template", detail: "Digests → Incidents digest.", href: "/digests" },
      { title: "On-call email", detail: "Delivery step — oncall@company.com.", href: "/digests" },
      { title: "Subject prefix", detail: "Incidents & risks — {{subject}}", href: "/digests" },
      { title: "Weekday cron", detail: "Default 0 8 * * 1-5 — 8am UTC weekdays.", href: "/digests" },
    ],
    integrations: ["Knowledge base (incident runbooks)", "Email"],
    tips: ["Surface open P1/P2 from indexed postmortems.", "Escalation footer included in message template."],
    links: [{ href: "/digests", label: "Digests" }],
  },
  {
    id: "digest_slack",
    category: "digests",
    name: "Slack summary",
    desc: "#ops channel pulse",
    tagline: "Mrkdwn-friendly digest to Slack webhook.",
    nodes: ["trigger", "retrieve", "llm", "notify", "output"],
    configure: [
      { title: "Slack webhook in Settings", detail: "Or override per-digest in Digests delivery step.", href: "/settings" },
      { title: "Message template", detail: "*{{subject}}*\\n\\n{{output}}\\n\\n_Powered by NovaFlow_", href: "/digests" },
      { title: "Schedule", detail: "Weekdays 9am default — adjust cron in step 4.", href: "/digests" },
    ],
    integrations: ["Slack webhook", "Knowledge base", "LLM"],
    tips: ["Use #ops or #product channel webhooks.", "Test with Developer Slack preset first."],
    links: [{ href: "/digests", label: "Digests" }],
  },
  {
    id: "digest_discord",
    category: "digests",
    name: "Discord digest",
    desc: "Community roundup",
    tagline: "Monday webhook post with markdown formatting.",
    nodes: ["trigger", "retrieve", "llm", "notify", "output"],
    configure: [
      { title: "Discord webhook", detail: "Settings → Integrations or per-digest override.", href: "/settings" },
      { title: "Weekly cron", detail: "Default Monday 10:00 UTC.", href: "/digests" },
      { title: "Message", detail: "**{{subject}}**\\n\\n{{output}}", href: "/digests" },
    ],
    integrations: ["Discord webhook", "Knowledge base"],
    tips: ["Ideal for community FAQ updates and handbook changes."],
    links: [{ href: "/digests", label: "Digests" }],
  },
  {
    id: "digest_telegram",
    category: "digests",
    name: "Telegram digest",
    desc: "Mobile-first brief",
    tagline: "Plain-text digest to chat ID.",
    nodes: ["trigger", "retrieve", "llm", "notify", "output"],
    configure: [
      { title: "Bot token", detail: "Settings → Telegram bot from @BotFather.", href: "/settings" },
      { title: "Chat ID", detail: "Digests delivery — e.g. -1001234567890 for groups.", href: "/digests" },
      { title: "Plain output", detail: "message={{output}} — no markdown required.", href: "/digests" },
    ],
    integrations: ["Telegram bot", "Knowledge base"],
    tips: ["Get chat_id by messaging bot then calling getUpdates.", "Daily 9am UTC default cron."],
    links: [{ href: "/digests", label: "Digests" }],
  },
  // Prompt templates
  {
    id: "prompt_support",
    category: "prompts",
    name: "Support triage",
    desc: "Customer reply + internal notes",
    tagline: "Used in Apps setup wizard and Build.",
    nodes: ["system prompt", "optional tools", "chat / assistant"],
    configure: [
      { title: "Projects → Assistants", detail: "Pick Support triage preset during assistant setup.", href: "/projects?tab=assistants" },
      { title: "Link knowledge", detail: "Attach KB for policy-aware answers.", href: "/knowledge" },
    ],
    integrations: ["LLM provider", "Optional KB"],
    tips: ["Empathetic tone baked into preset.", "Cite document names when relevant."],
    links: [{ href: "/projects?tab=assistants", label: "Projects" }],
  },
  {
    id: "prompt_docs",
    category: "prompts",
    name: "Document Q&A",
    desc: "Ground answers in retrieved files",
    tagline: "Direct answer + [n] citations structure.",
    nodes: ["assistant", "RAG retrieval", "chat"],
    configure: [
      { title: "Create app with docs preset", detail: "Setup wizard or Projects → Assistants.", href: "/projects?tab=assistants" },
      { title: "Upload documents", detail: "Knowledge base must be linked to assistant.", href: "/knowledge" },
      { title: "Chat", detail: "Uses rag_context_for_assistant at runtime with BM25+semantic RRF.", href: "/chat" },
    ],
    integrations: ["Knowledge base", "Embeddings provider"],
    tips: ["Says clearly when docs lack the answer.", "Works with multi-turn chat history."],
    links: [{ href: "/chat", label: "Chat" }],
  },
  {
    id: "prompt_analyst",
    category: "prompts",
    name: "Ops analyst",
    desc: "Findings · risks · next actions",
    tagline: "Executive summary format for leadership.",
    nodes: ["assistant", "chat"],
    configure: [
      { title: "Select in Projects", detail: "Ops analyst preset.", href: "/projects?tab=assistants" },
      { title: "Feed context", detail: "Paste metrics, incident text, or link KB.", href: "/knowledge" },
    ],
    integrations: ["LLM provider"],
    tips: ["Pair with research workflow template for scheduled briefs."],
    links: [{ href: "/projects?tab=assistants", label: "Projects" }],
  },
  {
    id: "prompt_writer",
    category: "prompts",
    name: "Writing helper",
    desc: "Polished drafts ready to send",
    tagline: "Tone-matching drafts with tighter alternatives.",
    nodes: ["assistant", "chat"],
    configure: [
      { title: "Projects assistant preset", detail: "Writing helper during create.", href: "/projects?tab=assistants" },
      { title: "No KB required", detail: "Works on user-provided text alone.", href: "/chat" },
    ],
    integrations: ["LLM provider"],
    tips: ["Use enrich workflow for bulk email polish."],
    links: [{ href: "/projects?tab=assistants", label: "Projects" }],
  },
  {
    id: "deploy_vercel",
    category: "deployment",
    name: "Vercel Frontend (Next.js 16)",
    desc: "Production Web UI & Edge Architecture",
    tagline: "Live App: https://nova-flow-ai-alpha.vercel.app",
    nodes: ["Next.js 16.2.10", "React 19.2.4", "Turbopack Compiler", "Vercel Global Edge Network"],
    configure: [
      { title: "Connect GitHub Repository", detail: "Import repository Ansh972007/NovaFlow-Ai into Vercel Dashboard with Next.js framework preset.", href: "https://vercel.com/new" },
      { title: "Configure Production API Target", detail: "Set NEXT_PUBLIC_API_URL=https://novaflow-ai.onrender.com to route REST endpoints and WSS streaming channels.", href: "/settings" },
      { title: "Enable Real-Time AIOS Chat", detail: "Set NEXT_PUBLIC_UNIVERSAL_CHAT_ENABLED=true and NEXT_PUBLIC_APP_NAME=NovaFlow AI.", href: "/chat" },
      { title: "Deploy & Edge Optimization", detail: "Trigger automatic Turbopack production build with sub-second asset hydration and edge caching.", href: "https://nova-flow-ai-alpha.vercel.app" },
    ],
    integrations: ["Vercel Edge Network", "GitHub Actions CI/CD", "Next.js App Router", "Turbopack"],
    tips: [
      "All WebSocket chat and graph streaming traffic derives dynamically from getApiBaseUrl() to wss://novaflow-ai.onrender.com.",
      "Production deployment is live with zero-downtime rolling updates at https://nova-flow-ai-alpha.vercel.app."
    ],
    links: [
      { href: "https://nova-flow-ai-alpha.vercel.app", label: "Live Production App ↗" },
      { href: "https://github.com/Ansh972007/NovaFlow-Ai", label: "GitHub Repository ↗" },
    ],
  },
  {
    id: "deploy_render",
    category: "deployment",
    name: "Render Docker API (FastAPI)",
    desc: "Production ASGI Kernel & WebSocket Gateway",
    tagline: "Live API: https://novaflow-ai.onrender.com",
    nodes: ["FastAPI 0.115.6", "Docker Linux Container", "Python 3.11+ Runtime", "Uvicorn ASGI Engine"],
    configure: [
      { title: "Create Render Web Service", detail: "Deploy Docker environment with Root Directory = backend and Dockerfile Path = Dockerfile.", href: "https://dashboard.render.com" },
      { title: "Configure Cloud Persistence", detail: "Inject DATABASE_URL (Supabase Session Pooler) and REDIS_URL (Upstash TLS rediss://).", href: "/credentials" },
      { title: "Cryptographic Vault Secrets", detail: "Supply 64-char JWT_SECRET, 32-byte ENCRYPTION_KEY, and FRONTEND_URL=https://nova-flow-ai-alpha.vercel.app.", href: "/settings" },
      { title: "Liveness Health Monitoring", detail: "Verify application lifecycle and container health probe at GET /api/health.", href: "https://novaflow-ai.onrender.com/api/health" },
    ],
    integrations: ["Render Cloud", "Docker Container", "FastAPI Kernel", "Uvicorn ASGI"],
    tips: [
      "Interactive OpenAPI documentation is live and testable at https://novaflow-ai.onrender.com/docs.",
      "Render handles automated TLS certificate renewal and zero-downtime container redeployment on git push."
    ],
    links: [
      { href: "https://novaflow-ai.onrender.com/docs", label: "Interactive Swagger Docs ↗" },
      { href: "https://novaflow-ai.onrender.com/api/health", label: "API Health Probe ↗" },
    ],
  },
  {
    id: "deploy_oauth",
    category: "deployment",
    name: "Google OAuth 2.0 (Gmail) Login",
    desc: "Zero-Trust Enterprise Identity & Callback",
    tagline: "Callback: https://novaflow-ai.onrender.com/api/v1/auth/oauth/google/callback",
    nodes: ["Google Cloud Console", "OAuth 2.0 PKCE", "Signed JWT State", "Gmail Security Scopes"],
    configure: [
      { title: "Google Cloud Credentials", detail: "Create an OAuth 2.0 Web Client ID in Google Cloud Console under APIs & Services.", href: "https://console.cloud.google.com" },
      { title: "Authorized JavaScript Origins", detail: "Register https://nova-flow-ai-alpha.vercel.app and https://novaflow-ai.onrender.com.", href: "/settings" },
      { title: "Authorized Redirect URIs", detail: "Register exact production callback: https://novaflow-ai.onrender.com/api/v1/auth/oauth/google/callback.", href: "/login" },
      { title: "Render Environment Secrets", detail: "Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET on Render dashboard.", href: "https://dashboard.render.com" },
    ],
    integrations: ["Google Cloud Identity", "Gmail OpenID Connect", "HMAC-SHA256 Token State"],
    tips: [
      "NovaFlow encodes return_to inside the cryptographic JWT state to dynamically redirect back to https://nova-flow-ai-alpha.vercel.app.",
      "Set GMAIL_ONLY_AUTH=1 in Render environment variables if you want to restrict login strictly to @gmail.com accounts."
    ],
    links: [
      { href: "/login", label: "Login Portal" },
      { href: "https://console.cloud.google.com", label: "Google Cloud Console ↗" },
    ],
  },
  {
    id: "deploy_db",
    category: "deployment",
    name: "Supabase & Upstash Infrastructure",
    desc: "Managed PostgreSQL 15 & Serverless Redis TLS",
    tagline: "Cloud Relational Store & Distributed Presence",
    nodes: ["Supabase PostgreSQL 15", "Upstash Redis TLS", "Hybrid Milvus / Vector Store", "Alembic Auto-Migrations"],
    configure: [
      { title: "Supabase PostgreSQL 15", detail: "Provision a free cloud database and copy the Session Pooler connection string on port 6543.", href: "https://supabase.com" },
      { title: "Upstash Serverless Redis", detail: "Create a Redis database with TLS enabled and copy the rediss:// TLS connection URL.", href: "https://upstash.com" },
      { title: "Automatic Schema Migrations", detail: "NovaFlow runs Alembic table synchronization automatically during Docker container boot.", href: "/developer" },
      { title: "Hybrid Vector Store Pipeline", detail: "Supports standalone Milvus 2.4.9 clusters with automated in-memory cosine vector store fallback.", href: "/knowledge" },
    ],
    integrations: ["Supabase Cloud", "Upstash Redis", "PostgreSQL 15", "Milvus Vector DB"],
    tips: [
      "Session pooler connection strings ensure zero socket starvation under high-concurrency serverless executions.",
      "Upstash Redis powers distributed sliding-window rate limiting and active user presence tracking."
    ],
    links: [
      { href: "/developer", label: "Developer Hub" },
      { href: "https://supabase.com", label: "Supabase Console ↗" },
    ],
  },
  {
    id: "deploy_telegram",
    category: "deployment",
    name: "Telegram Bot Integration Gateway",
    desc: "Multi-Tenant Webhook Dispatcher",
    tagline: "Webhook: https://novaflow-ai.onrender.com/api/v1/integrations/telegram/webhook",
    nodes: ["Telegram Bot API", "FastAPI Webhook Dispatcher", "AES-256 Secret Vault", "Interactive Command Routing"],
    configure: [
      { title: "Create Telegram Bot", detail: "Message @BotFather on Telegram with /newbot to generate your unique Bot Token.", href: "https://t.me/BotFather" },
      { title: "Store Encrypted Secret", detail: "Save your Bot Token inside the NovaFlow Credentials Vault (/credentials) with AES-256-GCM encryption.", href: "/credentials" },
      { title: "Webhook Registration", detail: "NovaFlow registers webhook target https://novaflow-ai.onrender.com/api/v1/integrations/telegram/webhook.", href: "/settings" },
      { title: "Mobile Conversational Testing", detail: "Send questions or /greetings commands directly from your mobile Telegram app.", href: "/chat" },
    ],
    integrations: ["Telegram Bot API", "NovaFlow Credentials Vault", "Real-Time AIOS Chat Engine"],
    tips: [
      "Supports multi-assistant routing, voice note speech-to-text transcripts, and automated alerts.",
      "Webhook secret token verification guarantees inbound payloads originate exclusively from Telegram servers."
    ],
    links: [
      { href: "/credentials", label: "Credentials Vault" },
      { href: "https://t.me/BotFather", label: "Telegram @BotFather ↗" },
    ],
  },
];

export function getTemplatesByCategory(categoryId) {
  if (categoryId === "nodes") return [];
  return TEMPLATE_DOCS.filter((t) => t.category === categoryId);
}
