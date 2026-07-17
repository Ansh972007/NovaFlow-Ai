"""
NovaFlow Enterprise AI Runtime — single orchestration layer for all AI capabilities.

Every AI request MUST flow through AIRuntime. Routers and services delegate here;
they must not assemble prompts, pick providers, or run tools directly.

Pipeline:
  Auth → PlatformContext → Permissions → Memory → Knowledge → Prompt Compiler
  → Model Router → Execution → Output Validation → Audit → Response
"""

from app.runtime.context import RuntimeContext, runtime_from_platform
from app.runtime.pipeline import AIRuntime, ChatRequest, ChatResult, AgentRequest, AgentResult

__all__ = [
    "RuntimeContext",
    "runtime_from_platform",
    "AIRuntime",
    "ChatRequest",
    "ChatResult",
    "AgentRequest",
    "AgentResult",
]
