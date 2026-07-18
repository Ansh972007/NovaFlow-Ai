# MCP Architecture

Location: `backend/app/connectivity/mcp.py`

## First-class MCP support

| Feature | Function |
|---------|----------|
| Registration | `register_mcp()` |
| Tool discovery | `discover_tools()` |
| Capability negotiation | `negotiate_capabilities()` |

## Roles

- `client` — discovers and invokes remote MCP tools
- `server` — exposes tools to AgentOS and workflows

## Transports

`stdio`, `sse`, `http` (configurable via `transport` + `endpoint`)

## Workspace isolation

Every MCP registration scoped to `workspace_id` with audit on register.

## API

- `POST /connectivity/mcp/register`
- `GET /connectivity/mcp`

## Context inheritance

MCP tool invocations inherit conversation, knowledge, workflow, and agent context via AgentOS integration hooks.
