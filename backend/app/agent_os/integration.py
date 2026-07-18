"""AgentOS integration — single execution path for all agent runs."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.agent_os.analytics import workspace_agent_analytics
from app.agent_os.communication import emit_agent_event
from app.agent_os.learning import record_learning
from app.agent_os.memory import load_agent_memory, load_conversation_history, memory_context
from app.agent_os.orchestration import run_consensus, run_team
from app.agent_os.planning import create_plan_session
from app.agent_os.reasoning import build_reasoning_trace, score_confidence, self_critique
from app.agent_os.safety import risk_score, scan_input, validate_tool_permissions
from app.agent_os.supervisor import evaluate_progress, supervise_plan
from app.agent_os.tasks import complete_run, create_run, fail_run, run_dict
from app.agent_os.verification import save_verification_report, verify_output
from app.runtime.agents import AgentLimits
from app.runtime.pipeline import AIRuntime, AgentRequest
from app.services.receipt import estimate_cost_usd


async def execute_agent(
    db: Session,
    ctx,
    *,
    user_input: str,
    agent_id: str = "",
    tools: list[str] | None = None,
    system: str = "",
    knowledge_id: int | None = None,
    conversation_id: str | None = None,
    mode: str = "single",
    roles: list[str] | None = None,
    agent_type: str = "custom",
    verify: bool = True,
    limits: AgentLimits | None = None,
) -> dict[str, Any]:
    """
    Single entry point for all platform agent execution.
    Used by REST API, workflow bridge, and future background workers.
    """
    from app.runtime.context import runtime_from_platform
    from app.conversation.integration import persist_agent_turn
    from app.database import SavedAgent
    from app.services.agent_tools import DEFAULT_AGENT_SYSTEM

    user_input = (user_input or "").strip()
    if not user_input:
        raise ValueError("input required")

    safety_scan = scan_input(user_input)
    if safety_scan.get("injection_detected"):
        emit_agent_event(
            db,
            "AgentSafetyAlert",
            workspace_id=ctx.workspace_id,
            agent_id=agent_id,
            organization_id=getattr(ctx, "organization_id", None),
            actor_user_id=ctx.user.user_id,
            payload=safety_scan,
        )

    if agent_id:
        agent = db.get(SavedAgent, agent_id)
        if not agent or agent.workspace_id != ctx.workspace_id:
            raise ValueError("Agent not found")
        try:
            tools = json.loads(agent.tools_json or "[]") or tools
        except json.JSONDecodeError:
            pass
        system = agent.system_prompt or system
        knowledge_id = agent.knowledge_id if knowledge_id is None else knowledge_id
        agent_type = getattr(agent, "agent_type", None) or agent_type
        lifecycle = getattr(agent, "lifecycle_status", None) or "published"
        if lifecycle not in ("published", "testing"):
            raise ValueError(f"Agent not executable in status: {lifecycle}")

    tools = tools or ["summarize"]
    valid_tools, rejected = validate_tool_permissions(tools if isinstance(tools, list) else [tools])
    if rejected:
        emit_agent_event(
            db,
            "AgentToolRejected",
            workspace_id=ctx.workspace_id,
            agent_id=agent_id,
            payload={"rejected": rejected},
        )

    risk = risk_score(
        tool_count=len(valid_tools),
        has_web_fetch="web_fetch" in valid_tools,
        injection_detected=safety_scan.get("injection_detected", False),
    )

    runtime_ctx = runtime_from_platform(ctx)
    trace_id = getattr(runtime_ctx, "trace_id", "") or ""

    run = create_run(
        db,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        input_text=user_input,
        agent_id=agent_id or None,
        mode=mode,
        organization_id=getattr(ctx, "organization_id", None),
        trace_id=trace_id,
    )

    emit_agent_event(
        db,
        "AgentRunStarted",
        workspace_id=ctx.workspace_id,
        run_id=run.id,
        agent_id=agent_id,
        organization_id=getattr(ctx, "organization_id", None),
        actor_user_id=ctx.user.user_id,
        payload={"mode": mode, "trace_id": trace_id},
    )

    plan_session = create_plan_session(db, workspace_id=ctx.workspace_id, goal=user_input, run_id=run.id)
    plan = json.loads(plan_session.plan_json or "{}")
    supervisor = supervise_plan(user_input, agent_type=agent_type) if mode in ("supervisor", "multi") else None

    memories = load_agent_memory(db, workspace_id=ctx.workspace_id, agent_id=agent_id or "default") if agent_id else []
    history = load_conversation_history(db, conversation_id=conversation_id, workspace_id=ctx.workspace_id)
    mem_ctx = memory_context(memories, history)
    system = (system or DEFAULT_AGENT_SYSTEM).strip()
    if mem_ctx:
        system = f"{system}\n\n{mem_ctx}"

    runtime = AIRuntime(runtime_ctx)
    try:
        if mode == "multi":
            payload = await run_team(
                runtime_ctx,
                user_input,
                mode="sequential",
                roles=roles,
                tool_ids=valid_tools,
                knowledge_id=knowledge_id,
                agent_type=agent_type,
            )
            output = payload.get("output") or ""
            tool_results = payload.get("tool_results") or []
            selected_tools = [t.get("tool") for t in tool_results if t.get("tool")]
            metrics = {"latency_ms": 0, "trace_id": trace_id}
        elif mode == "consensus":
            payload = await run_consensus(runtime_ctx, user_input, tool_ids=valid_tools, knowledge_id=knowledge_id)
            output = payload.get("output") or ""
            tool_results = payload.get("tool_results") or []
            selected_tools = [t.get("tool") for t in tool_results if t.get("tool")]
            metrics = {"latency_ms": 0, "trace_id": trace_id}
        else:
            result = await runtime.run_agent(
                AgentRequest(
                    user_input=user_input,
                    tool_ids=valid_tools,
                    system=system,
                    knowledge_id=knowledge_id,
                    agent_id=agent_id,
                    limits=limits,
                )
            )
            output = result.output
            tool_results = result.tool_results
            selected_tools = result.selected_tools
            metrics = result.metrics.to_dict()
    except Exception as exc:
        fail_run(db, run, str(exc))
        emit_agent_event(db, "AgentRunFailed", workspace_id=ctx.workspace_id, run_id=run.id, payload={"error": str(exc)[:200]})
        raise

    reasoning = build_reasoning_trace(goal=user_input, tool_results=tool_results, plan=plan)
    critique = self_critique(output, tool_results)

    verification_report = {}
    if verify:
        policies = {}
        if agent_id:
            agent = db.get(SavedAgent, agent_id)
            if agent:
                try:
                    policies = json.loads(getattr(agent, "policies_json", None) or "{}")
                except json.JSONDecodeError:
                    pass
        verification_report = verify_output(output=output, tool_results=tool_results, policies=policies)
        save_verification_report(db, run_id=run.id, workspace_id=ctx.workspace_id, report=verification_report)

    confidence = score_confidence(
        tool_results=tool_results,
        verification_verdict=verification_report.get("verdict", "pending"),
        output_length=len(output),
    )
    model = metrics.get("model") or ""
    cost = estimate_cost_usd(model, metrics.get("prompt_tokens"), metrics.get("completion_tokens"))

    conv_meta = persist_agent_turn(
        db,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        organization_id=getattr(ctx, "organization_id", None),
        agent_id=agent_id or "default-agent",
        user_input=user_input,
        output=output,
        conversation_id=conversation_id,
        tool_results=tool_results,
        selected_tools=selected_tools,
        metrics=metrics,
        knowledge_id=knowledge_id,
        trace_id=trace_id,
    )

    complete_run(
        db,
        run,
        output=output,
        plan=plan,
        reasoning=reasoning,
        verification=verification_report,
        metrics=metrics,
        confidence=confidence,
        cost_usd=cost,
        conversation_id=conv_meta.get("conversation_id"),
    )

    record_learning(
        db,
        run_id=run.id,
        agent_id=agent_id or None,
        workspace_id=ctx.workspace_id,
        success=verification_report.get("verdict") != "fail",
        tool_quality=min(1.0, len(tool_results) * 0.15),
        knowledge_quality=0.8 if any(t.get("tool") == "kb_search" for t in tool_results) else 0.3,
        latency_ms=int(metrics.get("latency_ms") or 0),
        cost_usd=cost,
        confidence=confidence,
        meta={"critique": critique, "risk": risk},
    )

    emit_agent_event(
        db,
        "AgentRunCompleted",
        workspace_id=ctx.workspace_id,
        run_id=run.id,
        agent_id=agent_id,
        payload={"confidence": confidence, "tool_calls": len(tool_results)},
    )

    return {
        "output": output,
        "tool_results": tool_results,
        "selected_tools": selected_tools,
        "metrics": metrics,
        "conversation_id": conv_meta.get("conversation_id"),
        "run_id": run.id,
        "run": run_dict(run),
        "plan": plan,
        "reasoning": reasoning,
        "verification": verification_report,
        "confidence": confidence,
        "critique": critique,
        "risk": risk,
        "supervisor": supervisor,
    }


async def execute_agent_from_runtime(
    runtime_ctx,
    user_input: str,
    *,
    tools: list[str] | None = None,
    system: str = "",
    knowledge_id: int | None = None,
    agent_id: str = "",
    mode: str = "single",
) -> dict[str, Any]:
    """Execute agent from workflow/runtime bridge with proper PlatformContext."""
    from app.database import User
    from app.platform.access import build_platform_context

    user = runtime_ctx.db.get(User, runtime_ctx.user_id)
    if not user:
        raise ValueError("User not found")
    platform = build_platform_context(
        runtime_ctx.db,
        user,
        workspace_id=runtime_ctx.workspace_id,
    )
    return await execute_agent(
        runtime_ctx.db,
        platform,
        user_input=user_input,
        agent_id=agent_id,
        tools=tools,
        system=system,
        knowledge_id=knowledge_id,
        mode=mode,
    )
