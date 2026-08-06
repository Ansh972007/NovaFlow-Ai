"""Dynamic content generation service for LLM-powered workflows."""

from typing import Any
from sqlalchemy.orm import Session
from app.runtime.context import RuntimeContext
from app.runtime.pipeline import AIRuntime, ChatRequest


class DynamicContentGenerator:
    """Generates dynamic content using LLM for various use cases."""
    
    def __init__(self, ctx: RuntimeContext):
        self.ctx = ctx
        self.runtime = AIRuntime(ctx)
    
    async def generate_email_content(
        self,
        subject: str,
        recipient: str,
        context: str = "",
        tone: str = "professional"
    ) -> dict[str, Any]:
        """Generate dynamic email content using LLM."""
        
        system_prompt = f"""You are an expert email writer. Generate a professional email based on the user's request.
The user wants to send an email about: {context or subject}
Generate a complete email with:
1. A compelling subject line (under 80 characters)
2. Professional greeting
3. Well-structured body paragraphs
4. Clear call-to-action
5. Professional closing

Make the email personalized, engaging, and appropriate for the context.
Tone: {tone}
Format your response as:
Subject: [your subject line]

[email body]

Keep the tone professional yet conversational."""
        
        request = ChatRequest(
            user_message=f"Generate an email about: {subject or context}. Recipient: {recipient}",
            system_prompt=system_prompt,
            history=[]
        )
        
        content = ""
        async for token in self.runtime.chat_stream(request):
            content += token
        
        # Parse the generated content
        lines = content.split('\n')
        email_subject = ""
        email_body = ""
        
        for i, line in enumerate(lines):
            if line.lower().startswith('subject:'):
                email_subject = line.split(':', 1)[1].strip()
                email_body = '\n'.join(lines[i+1:]).strip()
                break
        
        return {
            "subject": email_subject or f"Regarding: {subject}",
            "body": email_body or content,
            "recipient": recipient,
            "generated_content": content
        }
    
    async def generate_workflow_content(
        self,
        workflow_type: str,
        user_request: str,
        parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate dynamic content for workflow execution."""
        
        if workflow_type == "email":
            return await self.generate_email_content(
                subject=parameters.get("subject", user_request),
                recipient=parameters.get("recipient", ""),
                context=parameters.get("context", user_request),
                tone=parameters.get("tone", "professional")
            )
        
        # Add more workflow types as needed
        return {
            "error": f"Unsupported workflow type: {workflow_type}",
            "supported_types": ["email"]
        }


def get_dynamic_content_generator(db: Session, user_id: int, workspace_id: int) -> DynamicContentGenerator:
    """Factory function to create a dynamic content generator."""
    from app.runtime.context import RuntimeContext
    from app.deps import get_platform_ctx
    from fastapi import Request
    
    # Create a minimal request for context
    class MockRequest:
        def __init__(self):
            self.client = None
        @property
        def url(self):
            from urllib.parse import ParseResult
            return ParseResult(scheme="http", netloc="localhost", path="", params="", query="", fragment="")
    
    ctx = RuntimeContext.from_ws(
        db,
        user_id=user_id,
        workspace_id=workspace_id,
        role="editor",
        cancel_event=None
    )
    
    return DynamicContentGenerator(ctx)