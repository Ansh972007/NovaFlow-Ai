import asyncio
import json
import re
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.crypto import decode_token
from app.database import Assistant, ConversationAttachment, SessionLocal, User, Workflow
from app.deps import effective_role
from app.services.security_validator import validate_chat_request_security, SecurityValidationError
from app.services.tenancy import ensure_personal_workspace, get_membership
from app.services.knowledge import rag_hits_for_assistant
from app.services.workflow import log_usage, resolve_workflow_llm_messages, run_workflow_with_progress

router = APIRouter(tags=["Chat"])


def get_user_id_from_ws(websocket: WebSocket) -> int | None:
    from app.security.rate_limit import rate_limiter
    from app.security.config import RATE_LIMIT_WS_PER_MINUTE
    from app.security.tokens import session_is_active

    # Prefer Authorization header; fall back to query token for browser WS clients.
    token = None
    try:
        auth = websocket.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
        if not token:
            token = (
                websocket.query_params.get("t")
                or websocket.query_params.get("token")
                or websocket.query_params.get("access_token")
            )
        if not token:
            subprotocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
            for p in subprotocols:
                p = p.strip()
                if p.lower().startswith("bearer."):
                    token = p.split(".", 1)[1].strip()
                    break
                elif p.lower().startswith("bearer_"):
                    token = p.split("_", 1)[1].strip()
                    break
    except Exception as e:
        print(f"Error extracting token from WebSocket: {e}")
        return None
        
    if not token:
        return None
        
    try:
        client = websocket.client.host if websocket.client else "ws"
        if not rate_limiter.allow("ws", client, limit=RATE_LIMIT_WS_PER_MINUTE, window_seconds=60):
            print(f"Rate limit exceeded for WebSocket client: {client}")
            return None
            
        payload = decode_token(token)
        if not payload:
            print("Failed to decode WebSocket token")
            return None
            
        sid = payload.get("sid")
        if sid:
            db = SessionLocal()
            try:
                if not session_is_active(db, sid):
                    print("WebSocket session is not active")
                    return None
            except Exception as e:
                print(f"Error checking session activity: {e}")
                return None
            finally:
                db.close()
                
        return int(payload["sub"])
    except Exception as e:
        print(f"Error in get_user_id_from_ws: {e}")
        return None


def get_ws_workspace(db: Session, websocket: WebSocket, user_id: int) -> tuple[int, str] | None:
    """Resolve tenant for WebSocket — same kernel as HTTP (emergency + soft-delete)."""
    from app.platform.context import resolve_tenant
    from app.platform.emergency import expire_stale_grants
    from app.platform.permissions import workspace_has_permission
    from app.security.rbac import Permission

    user = db.get(User, user_id)
    if not user or user.delete:
        return None

    raw = websocket.query_params.get("workspace_id")
    wid = None
    if raw:
        try:
            wid = int(raw)
        except ValueError:
            return None

    expire_stale_grants(db)
    try:
        tenant = resolve_tenant(db, user, workspace_id=wid, request=None)
    except Exception:
        return None

    # Subscriptions require at least read permission on assistants/workflows
    if not workspace_has_permission(
        tenant.role,
        Permission.ASSISTANT_READ,
        via_emergency_access=tenant.via_emergency_access,
    ):
        return None

    return tenant.workspace_id, tenant.role

def _parse_user_message(payload: dict) -> str:
    from app.security.ai_guard import sanitize_user_prompt

    raw = (
        payload.get("inputs", {}).get("input")
        or payload.get("data", {}).get("dialog_input", {}).get("message")
        or payload.get("data", {}).get("dialog_input", {}).get("data", {}).get("user_input")
        or payload.get("message")
        or payload.get("query")
        or payload.get("content")
        or payload.get("input")
        or ""
    )
    return sanitize_user_prompt(str(raw))


def _parse_chat_history(payload: dict) -> list[dict]:
    """Accept prior turns from the client (role + content)."""
    raw = payload.get("chatHistory") or payload.get("history") or []
    if not isinstance(raw, list):
        return []
    out = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        role = (row.get("role") or "").strip().lower()
        if role not in ("user", "assistant"):
            continue
        content = (row.get("content") or row.get("message") or "").strip()
        if content:
            out.append({"role": role, "content": content})
    return out


def _parse_attachment_ids(payload: dict) -> list[str]:
    raw = payload.get("attachment_ids") or payload.get("attachmentIds") or []
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x or "").strip()][:20]


def handle_heartbeat(websocket: WebSocket, data: dict) -> bool:
    """Handle WebSocket heartbeat/ping messages."""
    if data.get("type") == "ping" or data.get("action") == "ping":
        try:
            import asyncio
            asyncio.create_task(websocket.send_json({"type": "pong"}))
        except Exception as e:
            print(f"Error sending pong: {e}")
        return True
    return False


def _attachment_texts(db: Session, *, workspace_id: int, attachment_ids: list[str]) -> list[str]:
    if not attachment_ids:
        return []
    rows = (
        db.query(ConversationAttachment)
        .filter(
            ConversationAttachment.workspace_id == workspace_id,
            ConversationAttachment.id.in_(attachment_ids),
            ConversationAttachment.deleted_at.is_(None),
        )
        .all()
    )
    texts: list[str] = []
    for row in rows:
        if not row.storage_key:
            continue
        p = UPLOAD_DIR / Path(row.storage_key)
        sidecar = p.with_suffix(p.suffix + ".txt")
        if sidecar.exists():
            try:
                txt = sidecar.read_text(encoding="utf-8", errors="ignore").strip()
                if txt:
                    texts.append(f"[Attachment: {row.file_name}]\n{txt[:8000]}")
            except Exception:
                pass
    return texts[:6]


async def _stream_reply(
    websocket: WebSocket,
    db: Session,
    user_id: int,
    resource_id: str,
    event_type: str,
    system: str,
    user_msg: str,
    workspace_id: int | None = None,
    receipt_extra: dict | None = None,
    cancel_event: asyncio.Event | None = None,
    history: list[dict] | None = None,
    *,
    assistant_id: str = "",
    rag_query: str | None = None,
    attachment_ids: list[str] | None = None,
):
    from app.runtime.context import RuntimeContext
    from app.runtime.pipeline import AIRuntime, ChatRequest
    from app.runtime.providers import resolve_provider
    from app.runtime.router import route_model
    from app.services.receipt import build_chat_receipt

    role = (receipt_extra or {}).get("role") or "editor"
    ctx = RuntimeContext.from_ws(
        db,
        user_id=user_id,
        workspace_id=workspace_id or 0,
        role=role,
        cancel_event=cancel_event,
    )
    runtime = AIRuntime(ctx)

    try:
        effective_user_id = (receipt_extra or {}).get("user_id") if receipt_extra else user_id
        try:
            validate_chat_request_security(db, effective_user_id)
        except SecurityValidationError as e:
            msg = (
                "Please configure your personal API key under Settings → API Keys to get custom responses. "
                "You can also ask general questions or request workflow automations!"
            )
            await websocket.send_json({"type": "start"})
            await websocket.send_json({"type": "stream", "message": {"content": msg, "reasoning_content": ""}})
            await websocket.send_json({"type": "end", "message": {"content": msg}, "receipt": {}})
            await websocket.send_json({"type": "close"})
            return

        conversation_api_key = (receipt_extra or {}).get("conversation_api_key")
        try:
            provider = resolve_provider(db, conversation_api_key, effective_user_id)
            route = route_model(db, workspace_id, provider)
        except Exception:
            provider = None
            route = None

        if not provider or not provider.api_key:
            msg = (
                "No active API key was found for your account. Please add your OpenAI/OpenRouter API key "
                "in Settings → API Keys to unlock full AI chat responses, or ask an admin to set up a global key."
            )
            await websocket.send_json({"type": "start"})
            await websocket.send_json({"type": "stream", "message": {"content": msg, "reasoning_content": ""}})
            await websocket.send_json({"type": "end", "message": {"content": msg}, "receipt": {}})
            await websocket.send_json({"type": "close"})
            return

        await websocket.send_json({"type": "start"})
        buffer = ""
        usage_out: dict = {}
        stopped = False
        rag_hits = (receipt_extra or {}).get("rag_hits")

        req = ChatRequest(
            user_message=user_msg,
            system_prompt=system,
            assistant_id=assistant_id,
            history=history,
            rag_query=rag_query or user_msg,
            conversation_api_key=conversation_api_key,
            user_id=effective_user_id,
            metadata=receipt_extra,
        )
        try:
            async for token in runtime.chat_stream(req, usage_out=usage_out):
                if cancel_event is not None and cancel_event.is_set():
                    stopped = True
                    break
                buffer += token
                await websocket.send_json(
                    {"type": "stream", "message": {"content": token, "reasoning_content": ""}}
                )
                await asyncio.sleep(0)
        except Exception as exc:
            err_msg = str(exc)
            if "401" in err_msg or "API key" in err_msg or "Unauthorized" in err_msg:
                fallback = (
                    "\n\n[Notice: The API key provided was invalid or expired. "
                    "Please update your API key in Settings → API Keys.]"
                )
                buffer += fallback
            elif not buffer:
                buffer = f"Response notice: {err_msg}"
            await websocket.send_json({"type": "stream", "message": {"content": buffer, "reasoning_content": ""}})
            await websocket.send_json({"type": "end", "message": {"content": buffer}, "receipt": {}})
            await websocket.send_json({"type": "close"})
            return

        if cancel_event is not None and cancel_event.is_set():
            stopped = True
        if not rag_hits and assistant_id:
            from app.runtime.knowledge import resolve_assistant_knowledge
            try:
                kb = resolve_assistant_knowledge(ctx, assistant_id, rag_query or user_msg)
                rag_hits = [h.to_dict() for h in kb.hits] if kb else []
            except Exception:
                rag_hits = []

        ab_meta = {"model": route.model, "variant": route.variant, "route_id": route.route_id} if route else None
        receipt = build_chat_receipt(
            model=ab_meta.get("model") if ab_meta else (usage_out.get("model") or ""),
            rag_hits=rag_hits,
            ab_meta=ab_meta,
            chars=len(buffer),
            event_type=event_type,
            usage=usage_out,
            stopped=stopped,
        )
        try:
            from app.composer.chat_powerhouse import accumulate_receipt

            accumulate_receipt(
                db,
                conversation_id=(receipt_extra or {}).get("conversation_id"),
                usage=usage_out,
                model=str(receipt.get("model") or ""),
            )
        except Exception:
            pass

        meta = {"chars": len(buffer), "stopped": stopped, "trace_id": ctx.trace_id}
        if usage_out.get("total_tokens") is not None:
            meta["total_tokens"] = usage_out.get("total_tokens")
            meta["prompt_tokens"] = usage_out.get("prompt_tokens")
            meta["completion_tokens"] = usage_out.get("completion_tokens")
        if ab_meta:
            meta["ab_variant"] = ab_meta.get("variant")
            meta["ab_model"] = ab_meta.get("model")
            meta["ab_route_id"] = ab_meta.get("route_id")
        log_usage(db, user_id, event_type, resource_id, meta, workspace_id)

        try:
            from app.conversation.integration import persist_chat_turn

            conv_meta = persist_chat_turn(
                db,
                workspace_id=workspace_id or 0,
                user_id=user_id,
                organization_id=None,
                assistant_id=assistant_id or resource_id,
                user_message=user_msg,
                assistant_message=buffer,
                conversation_id=(receipt_extra or {}).get("conversation_id"),
                usage=usage_out,
                rag_hits=rag_hits,
                trace_id=ctx.trace_id,
                event_type=event_type,
                attachment_ids=attachment_ids or [],
            )
            await websocket.send_json({"type": "conversation", "conversation_id": conv_meta.get("conversation_id")})
        except Exception:
            pass

        await websocket.send_json({"type": "end", "message": {"content": ""}, "receipt": receipt})
        await websocket.send_json({"type": "close"})

    except Exception as top_exc:
        err_text = f"Notice: {top_exc}"
        try:
            await websocket.send_json({"type": "start"})
            await websocket.send_json({"type": "stream", "message": {"content": err_text, "reasoning_content": ""}})
            await websocket.send_json({"type": "end", "message": {"content": err_text}, "receipt": {}})
            await websocket.send_json({"type": "close"})
        except Exception:
            pass
        meta = {"chars": len(buffer), "stopped": stopped, "trace_id": ctx.trace_id}
        if usage_out.get("total_tokens") is not None:
            meta["total_tokens"] = usage_out.get("total_tokens")
            meta["prompt_tokens"] = usage_out.get("prompt_tokens")
            meta["completion_tokens"] = usage_out.get("completion_tokens")
        if ab_meta:
            meta["ab_variant"] = ab_meta.get("variant")
            meta["ab_model"] = ab_meta.get("model")
            meta["ab_route_id"] = ab_meta.get("route_id")
        log_usage(db, user_id, event_type, resource_id, meta, workspace_id)

        try:
            from app.conversation.integration import persist_chat_turn

            conv_meta = persist_chat_turn(
                db,
                workspace_id=workspace_id or 0,
                user_id=user_id,
                organization_id=None,
                assistant_id=assistant_id or resource_id,
                user_message=user_msg,
                assistant_message=buffer,
                conversation_id=(receipt_extra or {}).get("conversation_id"),
                usage=usage_out,
                rag_hits=rag_hits,
                trace_id=ctx.trace_id,
                event_type=event_type,
                attachment_ids=attachment_ids or [],
            )
            await websocket.send_json({"type": "conversation", "conversation_id": conv_meta.get("conversation_id")})
        except Exception:
            pass
    except ValueError as e:
        # Handle missing API key gracefully in WebSocket
        if "No LLM provider configured" in str(e) or "No API key configured" in str(e):
            await websocket.send_json({"type": "start"})
            
            # Provide workflow management fallback
            try:
                from app.services.workflow_manager import WorkflowManager
                workflow_manager = WorkflowManager(db, user_id, workspace_id)
                suggestion = workflow_manager.suggest_workflow_action(user_msg)
                
                # Send as stream
                for line in suggestion.split('\n'):
                    await websocket.send_json({
                        "type": "stream", 
                        "message": {"content": line + "\n", "reasoning_content": ""}
                    })
                    await asyncio.sleep(0.1)
            except Exception:
                # Fallback to basic message
                fallback_msg = "I'd be happy to help you with that! However, to use AI features, you'll need to add your API key in **Settings → Model providers**. In the meantime, I can help you manage your workflows. Just ask me to list, run, test, or update your workflows!"
                await websocket.send_json({
                    "type": "stream", 
                    "message": {"content": fallback_msg, "reasoning_content": ""}
                })
            
            await websocket.send_json({"type": "end", "message": {"content": "", "receipt": {}}})
            await websocket.send_json({"type": "close"})
        else:
            raise


@router.websocket("/assistant/chat/{assistant_id}")
async def assistant_chat_ws(websocket: WebSocket, assistant_id: str):
    await websocket.accept()
    user_id = get_user_id_from_ws(websocket)
    if not user_id:
        await websocket.send_json({"type": "error", "category": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    db: Session = SessionLocal()
    try:
        ws_ctx = get_ws_workspace(db, websocket, user_id)
        if not ws_ctx:
            await websocket.send_json({"type": "error", "category": "error", "message": "Invalid workspace"})
            await websocket.close()
            return
        wid, role = ws_ctx

        assistant = db.get(Assistant, assistant_id)
        if not assistant or assistant.workspace_id != wid:
            assistant = db.query(Assistant).filter(Assistant.workspace_id == wid).first()
            if not assistant:
                default_prompt = (
                    "You are NovaFlow AI — a world-class, state-of-the-art AI OS Assistant & Workflow Composer created by Google Deepmind engineers. "
                    "Your responses must always be exceptionally helpful, beautifully formatted, highly structured, and warm.\n\n"
                    "Formatting Rules:\n"
                    "1. Always start with a concise executive summary or direct answer.\n"
                    "2. Use markdown headings (### Section) to organize complex topics into readable chunks.\n"
                    "3. Use bold bullet points for lists and key takeaways.\n"
                    "4. Wrap all code snippets, scripts, or JSON payloads in fenced markdown code blocks (` ```python ` or ` ```json `).\n"
                    "5. When creating or analyzing workflows, clearly outline step-by-step reasoning, required credentials/inputs, and execution flow.\n"
                    "6. Conclude with actionable next steps or recommendations."
                )
                assistant = Assistant(
                    id=assistant_id if len(assistant_id) > 10 else "default_assistant",
                    workspace_id=wid,
                    name="NovaFlow Assistant",
                    desc="Conversational workspace composer & AI assistant",
                    prompt=default_prompt,
                    status=1,
                )
                db.add(assistant)
                db.commit()
                db.refresh(assistant)

        init_raw = await websocket.receive_text()
        try:
            json.loads(init_raw)
        except json.JSONDecodeError:
            pass

        if assistant.desc:
            await websocket.send_json(
                {
                    "category": "guide_word",
                    "message": {"guide_word": assistant.desc, "msg": assistant.desc},
                }
            )

        assistant_cancel: asyncio.Event | None = None

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if payload.get("action") == "stop":
                if assistant_cancel is not None:
                    assistant_cancel.set()
                continue

            assistant_cancel = asyncio.Event()

            user_msg = _parse_user_message(payload)
            if not str(user_msg).strip():
                continue

            query = str(user_msg).strip()
            history = _parse_chat_history(payload)
            attachment_ids = _parse_attachment_ids(payload)
            conversation_id = payload.get("conversation_id") or websocket.query_params.get("conversation_id")
            if conversation_id and not history:
                try:
                    from app.conversation.integration import load_history_for_runtime

                    history = load_history_for_runtime(db, conversation_id, workspace_id=wid)
                except Exception:
                    pass
            # Prefer last user turn for retrieval; fall back to full query
            # Handle heartbeat/ping messages
            if handle_heartbeat(websocket, payload):
                continue

            rag_query = query
            if history:
                # Light rewrite: include previous user question for follow-ups
                prev_users = [h["content"] for h in history if h["role"] == "user"][-2:]
                if prev_users and len(query.split()) <= 8:
                    rag_query = f"{' '.join(prev_users[-1:])} {query}".strip()
            rag_hits = rag_hits_for_assistant(db, assistant_id, rag_query)
            system_prompt = assistant.prompt
            if re.search(r"\b(what day|what date|today|current date)\b", query, re.I):
                from datetime import datetime

                system_prompt = (
                    f"Current date: {datetime.now().strftime('%A, %B %d, %Y')}\n\n{system_prompt}"
                )
            attachment_context = _attachment_texts(db, workspace_id=wid, attachment_ids=attachment_ids)
            if attachment_context:
                query = query + "\n\nAttached context:\n" + "\n\n".join(attachment_context)

            try:
                from app.composer.chat_bridge import process_chat_turn

                bridge = await process_chat_turn(
                    db,
                    workspace_id=wid,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    user_message=str(user_msg).strip(),
                    workspace_role=role,
                )
            except Exception as bridge_exc:
                bridge = {
                    "events": [
                        {
                            "type": "aios_error",
                            "data": {
                                "message": str(bridge_exc)[:500],
                                "detail": "Workflow chat action failed",
                            },
                        }
                    ],
                    "ui_events": [
                        {
                            "type": "aios_error",
                            "data": {
                                "message": str(bridge_exc)[:500],
                                "detail": "Workflow chat action failed",
                            },
                        }
                    ],
                    "blocked_normal_reply": True,
                    "summary": f"Action failed: {bridge_exc}",
                }

            # Extract conversation API key from bridge if available
            conversation_api_key = (bridge.get("aios") or {}).get("conversation_api_key")

            for ev in (bridge.get("ui_events") or bridge.get("events") or []):
                # Send UI card(s) as helpful interactive attachments
                await websocket.send_json(ev)

            blocked = bool(bridge.get("blocked_normal_reply"))
            receipt_extra = {
                "rag_hits": rag_hits,
                "role": role,
                "conversation_id": conversation_id,
                "conversation_api_key": conversation_api_key,
                "planning_label": (bridge.get("aios") or {}).get("planning_label"),
                "planning_model": (bridge.get("aios") or {}).get("planning_model"),
                "planning_source": (bridge.get("aios") or {}).get("planning_source"),
                "user_id": user_id,
            }

            if blocked:
                # AIOS card is the full reply — skip generic LLM handbook stream
                summary_text = bridge.get("summary") or ""
                try:
                    from app.conversation.integration import persist_chat_turn

                    conv_meta = persist_chat_turn(
                        db,
                        workspace_id=wid,
                        user_id=user_id,
                        organization_id=None,
                        assistant_id=assistant_id,
                        user_message=str(user_msg).strip(),
                        assistant_message=summary_text or "Workflow action completed.",
                        conversation_id=conversation_id,
                        usage={},
                        rag_hits=rag_hits,
                        trace_id="",
                        event_type="assistant_chat",
                        attachment_ids=attachment_ids or [],
                    )
                    if conv_meta.get("conversation_id"):
                        conversation_id = conv_meta.get("conversation_id")
                except Exception:
                    pass
                await websocket.send_json(
                    {
                        "type": "end",
                        "message": summary_text,
                        "aios_only": True,
                        "receipt": {**receipt_extra, "conversation_id": conversation_id},
                    }
                )
            else:
                # Enrich prompt context with AIOS action summary for conversational streaming
                aios_summary = bridge.get("summary") or ""
                if aios_summary:
                    query = f"{query}\n\n[Workflow System Context: {aios_summary}]"

                try:
                    await _stream_reply(
                        websocket,
                        db,
                        user_id,
                        assistant_id,
                        "chat",
                        system_prompt,
                        query,
                        wid,
                        receipt_extra=receipt_extra,
                        cancel_event=assistant_cancel,
                        history=history,
                        assistant_id=assistant_id,
                        rag_query=rag_query,
                        attachment_ids=attachment_ids,
                    )
                finally:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        db.close()


@router.websocket("/workflow/chat/{workflow_id}")
async def workflow_chat_ws(websocket: WebSocket, workflow_id: str):
    await websocket.accept()
    user_id = get_user_id_from_ws(websocket)
    if not user_id:
        await websocket.send_json({"type": "error", "category": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    db: Session = SessionLocal()
    try:
        ws_ctx = get_ws_workspace(db, websocket, user_id)
        if not ws_ctx:
            await websocket.send_json({"type": "error", "category": "error", "message": "Invalid workspace"})
            await websocket.close()
            return
        wid, _role = ws_ctx

        workflow = db.get(Workflow, workflow_id)
        if not workflow or workflow.workspace_id != wid:
            await websocket.send_json({"type": "error", "category": "error", "message": "Workflow not found"})
            await websocket.close()
            return
        if workflow.status != 1:
            await websocket.send_json({"type": "error", "category": "error", "message": "Workflow is not published"})
            await websocket.close()
            return

        init_raw = await websocket.receive_text()
        try:
            json.loads(init_raw)
        except json.JSONDecodeError:
            pass

        if workflow.desc:
            await websocket.send_json(
                {
                    "category": "guide_word",
                    "message": {"guide_word": workflow.desc, "msg": workflow.desc},
                }
            )

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if payload.get("action") == "stop":
                continue

            # Handle heartbeat/ping messages
            if handle_heartbeat(websocket, payload):
                continue

            user_msg = _parse_user_message(payload)
            if not str(user_msg).strip():
                continue

            history = _parse_chat_history(payload)
            system, llm_user = await resolve_workflow_llm_messages(
                db, workflow, user_id, str(user_msg).strip()
            )
            cancel_event = asyncio.Event()

            async def _watch_stop(evt: asyncio.Event):
                while not evt.is_set():
                    try:
                        raw_stop = await websocket.receive_text()
                    except Exception:
                        evt.set()
                        return
                    try:
                        stop_payload = json.loads(raw_stop)
                    except json.JSONDecodeError:
                        continue
                    if stop_payload.get("action") == "stop":
                        evt.set()
                        return

            watcher = asyncio.create_task(_watch_stop(cancel_event))
            try:
                await _stream_reply(
                    websocket,
                    db,
                    user_id,
                    workflow.id,
                    "workflow_chat",
                    system,
                    llm_user,
                    wid,
                    cancel_event=cancel_event,
                    history=history,
                )
            finally:
                cancel_event.set()
                watcher.cancel()
                try:
                    await watcher
                except asyncio.CancelledError:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        db.close()


@router.websocket("/workflow/run/ws/{workflow_id}")
async def workflow_run_ws(websocket: WebSocket, workflow_id: str):
    await websocket.accept()
    user_id = get_user_id_from_ws(websocket)
    if not user_id:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    db: Session = SessionLocal()
    try:
        ws_ctx = get_ws_workspace(db, websocket, user_id)
        if not ws_ctx:
            await websocket.send_json({"type": "error", "message": "Invalid workspace"})
            await websocket.close()
            return
        wid, ws_role = ws_ctx

        user = db.get(User, user_id)
        if not user or user.delete:
            await websocket.send_json({"type": "error", "message": "Unauthorized"})
            await websocket.close()
            return
        from app.platform.roles import has_workspace_min_role

        if not has_workspace_min_role(ws_role, "editor"):
            await websocket.send_json({"type": "error", "message": "Viewer access is read-only"})
            await websocket.close()
            return

        workflow = db.get(Workflow, workflow_id)
        if not workflow or workflow.workspace_id != wid:
            await websocket.send_json({"type": "error", "message": "Workflow not found"})
            await websocket.close()
            return

        raw = await websocket.receive_text()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Invalid payload"})
            await websocket.close()
            return

        # Handle heartbeat/ping messages
        if handle_heartbeat(websocket, payload):
            # Continue to next message instead of returning
            pass

        user_input = (payload.get("input") or "").strip()
        if not user_input:
            await websocket.send_json({"type": "error", "message": "Input required"})
            await websocket.close()
            return

        async def emit(event: dict):
            await websocket.send_json(event)

        await run_workflow_with_progress(db, workflow, user_id, user_input, emit, workspace_id=wid)
        await websocket.send_json({"type": "close"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
