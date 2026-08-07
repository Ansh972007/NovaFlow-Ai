"""Global chat handler for general questions using user's API key.

Legacy auxiliary path for dynamic component / requirement gathering when no
structured HTTP config exists. Production chat compose uses `chat_bridge` /
`workflow_composer`; do not wire this as the primary assistant runtime.
"""

from typing import Dict, Optional
import httpx
import json


class GlobalChatHandler:
    """Handle general questions using user's API key."""
    
    def __init__(self, user_api_key: Optional[str] = None):
        self.user_api_key = user_api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "anthropic/claude-3.5-sonnet"  # Default model
    
    async def handle(self, user_input: str, entities: Dict, context: Optional[Dict] = None) -> str:
        """
        Handle general question using LLM API.
        
        Args:
            user_input: User's question
            entities: Extracted entities
            context: Conversation context
            
        Returns:
            AI response to the question
        """
        if not self.user_api_key:
            return self._generate_fallback_response(user_input)
        
        try:
            # Build conversation history from context
            messages = self._build_messages(user_input, context)
            
            # Call LLM API
            response = await self._call_llm_api(messages)
            
            return response
            
        except Exception as e:
            return self._generate_error_response(user_input, str(e))
    
    def _build_messages(self, user_input: str, context: Optional[Dict] = None) -> list:
        """Build message list for LLM API call."""
        system_prompt = """You are a helpful AI assistant with expertise in many domains:
- Programming and software development
- Business and productivity
- Creative writing and content
- Technical explanations
- General knowledge

Provide comprehensive, accurate, and helpful responses. If you're not certain about something, acknowledge it. Be concise but thorough."""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history if available
        if context and "history" in context:
            for msg in context["history"][-5:]:  # Last 5 messages
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    })
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages
    
    async def _call_llm_api(self, messages: list) -> str:
        """Call LLM API with user's key."""
        headers = {
            "Authorization": f"Bearer {self.user_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://novaflow.ai",
            "X-Title": "NovaFlow AI"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _generate_fallback_response(self, user_input: str) -> str:
        """Generate response when no API key is available."""
        return f"I'd be happy to help you with that question! However, to provide the most accurate and comprehensive answers, I need an API key configured.\n\nYour question: \"{user_input}\"\n\nTo enable full AI capabilities, please add your API key in **Settings → Model providers**. You can use providers like OpenRouter, OpenAI, or others.\n\nIn the meantime, I can still help you with:\n• Managing your workflows\n• Building new workflows\n• Running and testing workflows\n• General platform guidance\n\nWould you like me to help you with any of these, or would you prefer to add an API key first?"
    
    def _generate_error_response(self, user_input: str, error: str) -> str:
        """Generate response when API call fails."""
        return f"I tried to answer your question, but encountered an error: {error}\n\nYour question: \"{user_input}\"\n\nThis might be due to:\n• Invalid API key\n• API rate limits\n• Network issues\n\nPlease check your API key configuration in **Settings → Model providers** and try again. If the issue persists, let me know and I'll help you troubleshoot."
    
    def set_model(self, model: str):
        """Set the LLM model to use."""
        self.model = model
    
    def set_api_key(self, api_key: str):
        """Set the user's API key."""
        self.user_api_key = api_key