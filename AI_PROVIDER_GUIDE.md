# AI Provider Connection Guide

This document lists connection specifications and default parameters for NovaFlow's 22 supported cloud, local, and enterprise provider environments.

---

## 1. Supported Cloud Providers

| Provider ID | Label | Base URL | Default Model |
| :--- | :--- | :--- | :--- |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini` |
| `openai` | OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `anthropic` | Anthropic | `https://api.anthropic.com` | `claude-3-5-sonnet-latest` |
| `gemini` | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-1.5-flash` |
| `groq` | Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| `deepseek` | DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |

---

## 2. Local Deployments (Offline & Private)
For 100% offline workflow execution, run local inference engines and point NovaFlow to the local ports:

* **Ollama**:
  - *Base URL*: `http://localhost:11434/v1`
  - *Setup*: Run `ollama run llama3` to spin up local completion targets.
* **LM Studio**:
  - *Base URL*: `http://localhost:1234/v1`
  - *Setup*: Toggle "Local Server" inside the LM Studio app.
* **vLLM**:
  - *Base URL*: `http://localhost:8000/v1`

---

## 3. Enterprise Integration (Private Endpoints)
Configure secure setups for corporate private clouds:
* **Azure OpenAI**: Point `base_url` to your private cognitive service deployment endpoint.
* **AWS Bedrock / Google Vertex AI**: Connect via custom LiteLLM gateways.
