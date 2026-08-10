# Vision Provider Configuration

This document explains the current configuration and runtime details of the Vision Critic (Stage 11) within the BlendPilot system, specifically highlighting the recently added Groq integration.

## Current Configuration Overview
Based on the current state of the codebase, the implementation is configured to use **Groq** by default.

This is governed by:
1. `backend/config.py` where `default_llm_provider` is set to `"groq"`.
2. `services/llm.py` which automatically resolves the provider to `"groq"` if the `GROQ_API_KEY` environment variable is detected. (It falls back to OpenAI or Anthropic if their respective keys are found instead).

## Implementation Details

1. **Required Environment Variable:** 
   `GROQ_API_KEY`
2. **Groq Vision Model:** 
   The system maps the Groq provider to `llama-3.2-90b-vision-preview` for Vision Critic evaluations (defined in `LLMService.VISION_MODELS`).
3. **Where Provider is Configured:** 
   Defaults are established in `backend/config.py` (for the API schema) and `services/llm.py` (for direct code resolution).
4. **Is it Configurable?:** 
   Yes. It dynamically switches providers based on the keys present in `.env` and can be overridden via `LLMConfig`.
5. **Does the Model Support Vision?:** 
   Yes. The `llama-3.2-90b-vision-preview` model is a fully multimodal model capable of analyzing the image inputs.
6. **How `preview.png` is Passed:** 
   The image is read from the local disk, converted to a base64-encoded string, and embedded directly into a LangChain `HumanMessage` as a standard data URI (`data:image/png;base64,...`).
7. **Python Package/Client Used:** 
   The system utilizes the `langchain-groq` package, specifically instantiating the `ChatGroq` class to communicate with the Groq API.
8. **Other Required Environment Variables:** 
   None. Only the API key is required.

---

## What You Need to Configure

To enable real vision evaluation using Groq, you simply need to configure the following variable in your `.env` file:

```env
GROQ_API_KEY=
```
*(Do not commit this value or expose it publicly).*
