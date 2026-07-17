"""AI Runtime pipeline — single entry for chat, knowledge Q&A, and agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from app.runtime.agents import AgentLimits, run_agent_loop
from app.runtime.context import RuntimeContext
from app.runtime.execution import execute_chat_sync
from app.runtime.knowledge import KnowledgeBundle, resolve_assistant_knowledge, resolve_knowledge_base
from app.runtime.memory import MemoryBundle, MemoryRequest, resolve_memory
from app.runtime.observability import MetricsTimer, RuntimeMetrics, enrich_cost
from app.runtime.prompt import PromptInputs, compile_prompt
from app.runtime.providers import resolve_provider
from app.runtime.router import route_model
from app.runtime.streaming import stream_runtime_response, validate_stream_buffer
from app.runtime.validation import validate_markdown_output, validate_text_output
from app.security.ai_guard import detect_prompt_injection, sanitize_user_prompt
from app.security.rbac import Permission


@dataclass
class ChatRequest:
    user_message: str
    system_prompt: str = ""
    assistant_id: str = ""
    history: list[dict] | None = None
    rag_query: str = ""
    knowledge_id: int | None = None
    routing_policy: str = "default"
    workspace_context: str = ""


@dataclass
class ChatResult:
    content: str
    metrics: RuntimeMetrics
    knowledge: KnowledgeBundle = field(default_factory=KnowledgeBundle)
    memory: MemoryBundle = field(default_factory=MemoryBundle)
    compiled_system: str = ""


@dataclass
class AgentRequest:
    user_input: str
    tool_ids: list[str] = field(default_factory=list)
    system: str = ""
    knowledge_id: int | None = None
    agent_id: str = ""
    limits: AgentLimits | None = None


@dataclass
class AgentResult:
    output: str
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    selected_tools: list[str] = field(default_factory=list)
    metrics: RuntimeMetrics = field(default_factory=RuntimeMetrics)


class AIRuntime:
    """Enterprise AI orchestration layer."""

    def __init__(self, ctx: RuntimeContext) -> None:
        self.ctx = ctx

    def _guard_input(self, text: str) -> str:
        cleaned = sanitize_user_prompt(text)
        reason = detect_prompt_injection(cleaned)
        if reason:
            from fastapi import HTTPException

            self.ctx.audit("ai.prompt_injection_blocked", detail={"reason": reason})
            raise HTTPException(status_code=400, detail="Message blocked by security policy")
        return cleaned

    def _build_chat_prompt(
        self,
        req: ChatRequest,
        *,
        knowledge: KnowledgeBundle | None = None,
        memory: MemoryBundle | None = None,
    ) -> tuple[str, str, KnowledgeBundle, MemoryBundle]:
        mem = memory or resolve_memory(
            self.ctx,
            MemoryRequest(
                history=req.history,
                assistant_id=req.assistant_id,
                session_id=self.ctx.session_id,
                query=req.rag_query or req.user_message,
            ),
        )
        kb = knowledge
        if kb is None and req.assistant_id:
            kb = resolve_assistant_knowledge(
                self.ctx,
                req.assistant_id,
                req.rag_query or req.user_message,
            )
        elif kb is None and req.knowledge_id:
            kb = resolve_knowledge_base(
                self.ctx,
                req.knowledge_id,
                req.rag_query or req.user_message,
            )
        else:
            kb = kb or KnowledgeBundle()

        compiled = compile_prompt(
            PromptInputs(
                system_prompt=req.system_prompt,
                workspace_context=req.workspace_context,
                knowledge_context=kb.context,
                memory_context=mem.combined(),
                conversation_context="",
                user_prompt=req.user_message,
            )
        )
        return compiled.system, compiled.user, kb, mem

    async def chat_stream(
        self,
        req: ChatRequest,
        *,
        usage_out: dict | None = None,
    ) -> AsyncIterator[str]:
        """Full pipeline for streaming chat."""
        self.ctx.require_permission(Permission.ASSISTANT_READ)
        user_msg = self._guard_input(req.user_message)
        req = ChatRequest(**{**req.__dict__, "user_message": user_msg})

        timer = MetricsTimer()
        provider = resolve_provider(self.ctx.db)
        route = route_model(
            self.ctx.db, self.ctx.workspace_id, provider, policy=req.routing_policy
        )
        metrics = RuntimeMetrics(
            trace_id=self.ctx.trace_id,
            provider=provider.provider_type,
            model=route.model,
            policy=route.policy,
        )

        system, user, kb, mem = self._build_chat_prompt(req)
        metrics.knowledge_hits = kb.hit_count
        metrics.cache_hit = kb.cache_hit

        usage = usage_out if usage_out is not None else {}
        async for token in stream_runtime_response(
            self.ctx,
            system,
            user,
            history=req.history,
            metrics=metrics,
            usage_out=usage,
        ):
            yield token

        metrics.latency_ms = timer.elapsed_ms()
        self.ctx.audit(
            "ai.chat.complete",
            detail={
                "assistant_id": req.assistant_id,
                "model": metrics.model,
                "knowledge_hits": metrics.knowledge_hits,
                "latency_ms": metrics.latency_ms,
            },
            resource_type="assistant",
            resource_id=req.assistant_id,
        )

    async def chat(self, req: ChatRequest) -> ChatResult:
        """Non-streaming chat through full pipeline."""
        self.ctx.require_permission(Permission.ASSISTANT_READ)
        user_msg = self._guard_input(req.user_message)
        req = ChatRequest(**{**req.__dict__, "user_message": user_msg})

        timer = MetricsTimer()
        provider = resolve_provider(self.ctx.db)
        route = route_model(
            self.ctx.db, self.ctx.workspace_id, provider, policy=req.routing_policy
        )
        metrics = RuntimeMetrics(
            trace_id=self.ctx.trace_id,
            provider=provider.provider_type,
            model=route.model,
            policy=route.policy,
        )

        system, user, kb, mem = self._build_chat_prompt(req)
        metrics.knowledge_hits = kb.hit_count
        metrics.cache_hit = kb.cache_hit

        raw = await execute_chat_sync(self.ctx, system, user, history=req.history, policy=req.routing_policy)
        validated = validate_markdown_output(raw)
        metrics.latency_ms = timer.elapsed_ms()
        enrich_cost(metrics)

        self.ctx.audit(
            "ai.chat.complete",
            detail={"model": metrics.model, "knowledge_hits": metrics.knowledge_hits},
            resource_type="assistant",
            resource_id=req.assistant_id,
        )
        return ChatResult(
            content=validated.content,
            metrics=metrics,
            knowledge=kb,
            memory=mem,
            compiled_system=system,
        )

    async def knowledge_answer(
        self,
        knowledge_id: int,
        query: str,
        *,
        system_override: str = "",
        limit: int = 5,
    ) -> ChatResult:
        """Grounded Q&A over a knowledge base."""
        self.ctx.require_permission(Permission.KNOWLEDGE_READ)
        query = self._guard_input(query)

        from app.database import KnowledgeBase

        kb_row = self.ctx.db.get(KnowledgeBase, knowledge_id)
        if not kb_row or kb_row.workspace_id != self.ctx.workspace_id:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Knowledge base not found")

        kb = resolve_knowledge_base(self.ctx, knowledge_id, query, limit=limit)
        system = system_override or (
            f"You answer questions using only the retrieved passages from knowledge base «{kb_row.name}». "
            "Lead with a direct answer, then 2–4 short supporting bullets. "
            "Cite sources as [n] when you rely on a passage. "
            "If the passages do not contain the answer, say what is missing — do not invent facts."
        )
        compiled = compile_prompt(
            PromptInputs(
                system_prompt=system,
                knowledge_context=kb.context,
                user_prompt=f"## Question\n{query}",
            )
        )
        timer = MetricsTimer()
        provider = resolve_provider(self.ctx.db)
        route = route_model(self.ctx.db, self.ctx.workspace_id, provider)
        metrics = RuntimeMetrics(
            trace_id=self.ctx.trace_id,
            provider=provider.provider_type,
            model=route.model,
            knowledge_hits=kb.hit_count,
            cache_hit=kb.cache_hit,
        )
        raw = await execute_chat_sync(self.ctx, compiled.system, compiled.user)
        validated = validate_markdown_output(raw)
        metrics.latency_ms = timer.elapsed_ms()
        enrich_cost(metrics)
        self.ctx.audit(
            "ai.knowledge.answer",
            detail={"knowledge_id": knowledge_id, "hits": kb.hit_count},
            resource_type="knowledge",
            resource_id=str(knowledge_id),
        )
        return ChatResult(
            content=validated.content,
            metrics=metrics,
            knowledge=kb,
            compiled_system=compiled.system,
        )

    async def run_agent(self, req: AgentRequest) -> AgentResult:
        """Agent execution with tool runtime."""
        self.ctx.require_permission(Permission.AGENT_RUN)
        user_input = self._guard_input(req.user_input)

        timer = MetricsTimer()
        payload = await run_agent_loop(
            self.ctx,
            user_input,
            req.tool_ids,
            system=req.system,
            knowledge_id=req.knowledge_id,
            limits=req.limits,
        )
        validated = validate_text_output(payload.get("output") or "")
        metrics = RuntimeMetrics(trace_id=self.ctx.trace_id)
        metrics.tool_calls = len(payload.get("tool_results") or [])
        metrics.latency_ms = timer.elapsed_ms()

        self.ctx.audit(
            "ai.agent.complete",
            detail={
                "agent_id": req.agent_id,
                "tools": payload.get("selected_tools"),
                "tool_calls": metrics.tool_calls,
            },
            resource_type="agent",
            resource_id=req.agent_id,
        )
        return AgentResult(
            output=validated.content,
            tool_results=payload.get("tool_results") or [],
            selected_tools=payload.get("selected_tools") or [],
            metrics=metrics,
        )
