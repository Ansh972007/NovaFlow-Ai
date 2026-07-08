/** Canonical workflow starter templates — always show all in the UI. */
export const WORKFLOW_TEMPLATES = [
  { id: "rag", name: "RAG Q&A pipeline", desc: "Retrieve docs then answer with LLM" },
  { id: "support", name: "Support triage", desc: "Classify and draft support replies" },
  { id: "research", name: "Research brief", desc: "Retrieve sources and synthesize a brief" },
  { id: "enrich", name: "Transform + LLM", desc: "Format input with a template then run LLM" },
  { id: "agent_loop", name: "Agent + review", desc: "Tool agent with human review gate" },
  { id: "batch", name: "Batch loop", desc: "Process each line of input in parallel tasks" },
  { id: "telegram_qa", name: "Telegram Q&A bot", desc: "Answer questions and reply via Telegram" },
  { id: "daily_digest", name: "Daily digest email", desc: "Retrieve knowledge and email a summary" },
  { id: "jira_ticket", name: "Jira ticket from input", desc: "Create a Jira issue from workflow output" },
  { id: "slack_alert", name: "Slack alert", desc: "Summarize input and post to Slack" },
  { id: "github_issue", name: "GitHub issue from input", desc: "Create a GitHub issue from workflow output" },
  { id: "discord_alert", name: "Discord alert", desc: "Summarize input and post to Discord" },
  { id: "linear_issue", name: "Linear issue from input", desc: "Create a Linear issue from workflow output" },
];

export function mergeWorkflowTemplates(apiTemplates) {
  if (!Array.isArray(apiTemplates) || apiTemplates.length === 0) {
    return WORKFLOW_TEMPLATES;
  }
  const byId = new Map(apiTemplates.map((t) => [t.id, t]));
  return WORKFLOW_TEMPLATES.map((base) => ({ ...base, ...byId.get(base.id) }));
}
