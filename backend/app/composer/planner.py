import json
import re
from typing import Any
from sqlalchemy.orm import Session
from app.database import ProjectGraph, SolutionGraph, HierarchicalMemory
from app.composer.reuse import match_reusable_asset
from app.composer.gap_analysis import analyze_solution_gaps
from app.composer.recipes import match_recipe, progress_steps
from app.composer.workflow_composer import build_executable_graph


def parse_goal_intent(goal: str) -> list[str]:
    """Identify required system capabilities based on natural language goal keywords."""
    return infer_capabilities_from_goal(goal)


def infer_capabilities_from_goal(
    goal: str,
    *,
    force_workflow: bool = False,
    llm_cfg: dict | None = None,
) -> list[str]:
    """Heuristic (+ optional LLM) capability inference for any field goal."""
    goal_lower = (goal or "").lower()
    required: list[str] = []
    recipe = match_recipe(goal, fallback_generic=False)
    if recipe:
        required.extend(recipe.get("caps") or [])

    if "voice" in goal_lower or "audio" in goal_lower:
        required.append("cap_voice")
    if any(k in goal_lower for k in ("workflow", "automate", "automation", "process", "pipeline")):
        required.append("cap_workflow")
    if any(k in goal_lower for k in ("knowledge", "docs", "rag", "document", "from my", "invoice", "onboard", "policy")):
        required.append("cap_knowledge")
    if "ocr" in goal_lower or "image" in goal_lower:
        required.append("cap_ocr")
    if "telegram" in goal_lower or ("bot" in goal_lower and "robot" not in goal_lower and "whatsapp" not in goal_lower):
        required.append("cap_telegram")
    if "slack" in goal_lower:
        required.append("cap_slack")
    if "discord" in goal_lower:
        required.append("cap_discord")
    if "github" in goal_lower:
        required.append("cap_github")
    if "jira" in goal_lower:
        required.append("cap_jira")
    if "linear" in goal_lower:
        required.append("cap_linear")
    if any(k in goal_lower for k in ("whatsapp", "whats app", "wa business")):
        required.append("cap_whatsapp")
    if "youtube" in goal_lower or "yt channel" in goal_lower or re.search(r"\byt\b", goal_lower):
        required.append("cap_youtube")
    if "shopify" in goal_lower:
        required.append("cap_shopify")
    if any(
        k in goal_lower
        for k in (
            "google auth", "google oauth", "google api", "google sheets", "google drive", "gdrive",
            "google calendar", "gcal", "spreadsheet", "excel",
        )
    ):
        required.append("cap_google")
    if any(
        k in goal_lower
        for k in (
            "outlook", "microsoft 365", "office 365", "ms graph", "microsoft graph",
            "outlook calendar", "microsoft calendar", "onedrive", "sharepoint", "excel online",
        )
    ):
        required.append("cap_outlook")
    if any(k in goal_lower for k in ("calendar", "calander", "meeting", "meetings", "appointment")):
        if "outlook" in goal_lower or "microsoft" in goal_lower:
            required.append("cap_outlook")
        else:
            required.append("cap_google")
    if any(k in goal_lower for k in ("calendar", "calendar event")) and "google" in goal_lower:
        required.append("cap_google")
    if any(k in goal_lower for k in ("calendar", "calendar event")) and (
        "outlook" in goal_lower or "microsoft" in goal_lower
    ):
        required.append("cap_outlook")
    youtube_primary = bool(re.search(r"\byoutube\b|\byt\s+channel\b", goal_lower))
    if any(k in goal_lower for k in ("email", "smtp", "mail", "welcome email", "reminder", "gmail")):
        # Prefer Outlook cap when Outlook mentioned; else SMTP
        if "outlook" not in goal_lower and "microsoft" not in goal_lower:
            required.append("cap_smtp")
    elif "digest" in goal_lower and not youtube_primary:
        required.append("cap_smtp")
    if any(k in goal_lower for k in ("webhook", "http call", "call api", "lead capture", "crm")):
        required.append("cap_http")
        required.append("cap_workflow")
    if any(k in goal_lower for k in ("csv", "etl", "pipeline", "transform")):
        required.append("cap_workflow")
    if any(k in goal_lower for k in ("agent", "multi-agent", "supervisor")):
        required.append("cap_workflow")
        required.append("cap_agent")
    if any(k in goal_lower for k in ("schedule", "cron", "monday", "every day", "weekly")):
        required.append("cap_workflow")
    if any(k in goal_lower for k in ("support", "ticket", "helpdesk", "hr", "hire", "sales", "expense", "finance", "content", "blog")):
        required.append("cap_workflow")

    # Merge channel-registry detections
    try:
        from app.composer.chat_channels import caps_from_goal

        required.extend(caps_from_goal(goal))
    except Exception:  # noqa: BLE001
        pass

    required = list(dict.fromkeys(required))
    if not required and (force_workflow or goal_lower.strip()):
        # Optional short LLM JSON when heuristics empty
        llm_caps = _llm_infer_caps(goal, llm_cfg)
        if llm_caps:
            required = llm_caps
        else:
            required = ["cap_workflow"]
            if any(k in goal_lower for k in ("doc", "knowledge", "document", "policy", "invoice")):
                required.append("cap_knowledge")
    if force_workflow and "cap_workflow" not in required:
        required.insert(0, "cap_workflow")
    return list(dict.fromkeys(required))


def _llm_infer_caps(goal: str, llm_cfg: dict | None = None) -> list[str]:
    """Best-effort LLM capability list; never raises. Skips when no LLM helper."""
    try:
        import json
        import re

        from app.services.llm import complete_text

        cfg = llm_cfg or {}
        if not cfg.get("api_key"):
            return []
        raw = complete_text(
            system=(
                "Return a JSON array of capability ids only from: "
                "cap_workflow, cap_knowledge, cap_telegram, cap_slack, cap_discord, "
                "cap_smtp, cap_github, cap_jira, cap_linear, cap_http, cap_agent, cap_voice, cap_ocr, "
                "cap_whatsapp, cap_youtube, cap_shopify, cap_google, cap_outlook. "
                "Always include cap_workflow for automation goals."
            ),
            user=f"Goal: {(goal or '')[:800]}",
            cfg=cfg,
        )
        match = re.search(r"\[[\s\S]*\]", str(raw or ""))
        if not match:
            return []
        data = json.loads(match.group(0))
        allowed = {
            "cap_workflow",
            "cap_knowledge",
            "cap_telegram",
            "cap_slack",
            "cap_discord",
            "cap_smtp",
            "cap_github",
            "cap_jira",
            "cap_linear",
            "cap_http",
            "cap_agent",
            "cap_voice",
            "cap_ocr",
        }
        return [c for c in data if isinstance(c, str) and c in allowed][:8]
    except Exception:
        return []

def compile_solution_blueprint(
    db: Session,
    workspace_id: int,
    goal: str,
    *,
    requirements: dict[str, Any] | None = None,
    materialize_workflow: bool = True,
    workflow_name: str | None = None,
) -> dict:
    """Design the solution blueprint, matching reuse options and running gap checks."""
    reused = match_reusable_asset(db, workspace_id, goal)
    reuse_note = None
    if reused:
        reuse_note = {
            "source_id": reused.get("id"),
            "source_type": reused.get("type"),
            "source_name": reused.get("name"),
        }
        caps = []
        graph = reused.get("graph") or {}
        if isinstance(graph, dict):
            caps = list(graph.get("required_capabilities") or [])
        if not caps:
            caps = parse_goal_intent(goal)
        required_caps = caps or parse_goal_intent(goal)
        missing_creds = analyze_solution_gaps(db, workspace_id, required_caps)
        graph_payload = {
            "nodes": graph.get("nodes") if isinstance(graph, dict) else {},
            "edges": graph.get("edges") if isinstance(graph, dict) else [],
            "required_capabilities": required_caps,
            "reused_from": reuse_note,
        }
        if not required_caps:
            required_caps = parse_goal_intent(goal)
            graph_payload["required_capabilities"] = required_caps
    else:
        required_caps = infer_capabilities_from_goal(goal, force_workflow=True)
        missing_creds = analyze_solution_gaps(db, workspace_id, required_caps)
        nodes = {}
        edges = []
        for cap_id in required_caps:
            nodes[cap_id] = {
                "type": "capability",
                "id": cap_id,
                "status": "ready" if cap_id not in missing_creds else "pending_credentials",
            }
        if "store" in goal.lower() or "menu" in goal.lower() or "database" in goal.lower():
            nodes["db_orders"] = {
                "type": "database",
                "schema_name": "orders",
                "fields": ["id", "customer_name", "items", "total_price"],
            }
            for cap_id in required_caps:
                edges.append({"source": cap_id, "target": "db_orders"})
        graph_payload = {
            "nodes": nodes,
            "edges": edges,
            "required_capabilities": required_caps,
        }

    recipe = match_recipe(goal, fallback_generic=True)
    if recipe:
        graph_payload["recipe"] = {
            "id": recipe.get("id"),
            "name": recipe.get("name"),
            "description": recipe.get("description"),
            "field": recipe.get("field"),
        }
    if not required_caps:
        required_caps = list(recipe.get("caps") or ["cap_workflow"]) if recipe else ["cap_workflow"]
        graph_payload["required_capabilities"] = required_caps
        missing_creds = analyze_solution_gaps(db, workspace_id, required_caps)

    project = ProjectGraph(
        workspace_id=workspace_id,
        name=f"Project: {goal[:30]}...",
        business_goal=goal,
        status="compiled_draft" if missing_creds else "active",
        solution_payload=json.dumps(graph_payload),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    solution = SolutionGraph(
        project_id=project.id,
        graph_payload=json.dumps(graph_payload),
        status="compiled_draft" if missing_creds else "compiled",
    )
    db.add(solution)
    db.commit()
    db.refresh(solution)

    memory = HierarchicalMemory(
        workspace_id=workspace_id,
        scope="solution",
        scope_ref=solution.id,
        content=f"Initial compilation memory context for goal: {goal}",
    )
    db.add(memory)
    db.commit()

    executable = build_executable_graph(
        required_caps=required_caps,
        goal=goal,
        knowledge_id=None,
        recipe_id=(recipe or {}).get("id"),
        requirements=requirements,
        db=db,
        workspace_id=workspace_id,
    )

    def _smart_wf_name(g_text: str, caps_list: list[str]) -> str:
        if workflow_name and str(workflow_name).strip():
            return str(workflow_name).strip()
        raw = (g_text or "").strip()
        if not raw or raw.lower() in ("user input", "none", "test", "build a workflow for this"):
            if "cap_smtp" in caps_list:
                return "Multi-Subject Email Dispatcher Workflow"
            if "cap_telegram" in caps_list:
                return "Telegram AI Assistant Bot Workflow"
            if "cap_github" in caps_list:
                return "GitHub Issue Triage Workflow"
            return "Custom Automated Workflow"
        clean = re.sub(r"^(build|create|make|compose)\s+(a\s+)?(workflow\s+(to\s+)?|bot\s+(for\s+)?|automation\s+(for\s+)?)?", "", raw, flags=re.I).strip()
        if not clean:
            clean = raw
        words = [w.capitalize() for w in clean.split()[:6]]
        name_str = " ".join(words)
        return name_str if name_str.lower().endswith("workflow") else f"{name_str} Workflow"

    smart_name = _smart_wf_name(goal, required_caps)

    created_workflow_id = None
    if materialize_workflow:
        try:
            from app.database import Workflow
            wf = Workflow(
                name=smart_name,
                desc=f"Compiled workflow for goal: {goal}",
                graph_json=json.dumps({"nodes": executable.get("nodes") or [], "edges": executable.get("edges") or []}),
                user_id=1,
                workspace_id=workspace_id,
                status=1,
            )
            db.add(wf)
            db.commit()
            db.refresh(wf)
            created_workflow_id = wf.id
        except Exception:
            pass

    if reuse_note:
        api_status = "reused"
    elif missing_creds:
        api_status = "compiled_draft"
    else:
        api_status = "active"

    out = {
        "project_id": project.id,
        "solution_id": solution.id,
        "workflow_id": created_workflow_id,
        "status": api_status,
        "graph": graph_payload,
        "executable_preview": executable,
        "missing_credentials": missing_creds,
        "required_capabilities": required_caps,
        "node_types": (executable.get("meta") or {}).get("node_types") or [],
        "recipe": graph_payload.get("recipe"),
        "recipe_name": (recipe or {}).get("name"),
        "progress": progress_steps(missing_credentials=missing_creds, mode="workflow"),
        "next_action": "credentials" if missing_creds else "approve",
    }
    if reuse_note:
        out["type"] = reuse_note.get("source_type") or "reused"
        out["reused_from"] = reuse_note
    return out
