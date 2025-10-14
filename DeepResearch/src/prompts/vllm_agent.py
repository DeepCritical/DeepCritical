"""
VLLM Agent prompts for DeepCritical research workflows.

This module defines system prompts and instructions for VLLM agent operations.
"""

# System prompt for VLLM agent
VLLM_AGENT_SYSTEM_PROMPT = """You are a helpful AI assistant powered by VLLM. You can perform various tasks including text generation, conversation, and analysis.

You have access to various tools for:
- Chat completion with the VLLM model
- Text completion and generation
- Embedding generation
- Model information and management
- Tokenization operations

Use these tools appropriately to help users with their requests."""

# Prompt templates for VLLM operations
VLLM_AGENT_PROMPTS: dict[str, str] = {
    "system": VLLM_AGENT_SYSTEM_PROMPT,
    "chat_completion": """Chat with the VLLM model using the following parameters:

Messages: {messages}
Model: {model}
Temperature: {temperature}
Max tokens: {max_tokens}
Top-p: {top_p}

Provide a helpful response based on the conversation context.""",
    "text_completion": """Complete the following text using the VLLM model:

Prompt: {prompt}
Model: {model}
Temperature: {temperature}
Max tokens: {max_tokens}

Generate a coherent continuation of the provided text.""",
    "embedding_generation": """Generate embeddings for the following texts:

Texts: {texts}
Model: {model}

Return the embedding vectors for each input text.""",
    "model_info": """Get information about the model: {model_name}

Provide details about the model including:
- Model type and architecture
- Supported features
- Performance characteristics""",
    "tokenization": """Tokenize the following text:

Text: {text}
Model: {model}

Return the token IDs and token strings.""",
    "detokenization": """Detokenize the following token IDs:

Token IDs: {token_ids}
Model: {model}

Return the original text.""",
    "health_check": """Check the health of the VLLM server:

Server URL: {server_url}

Return server status and health metrics.""",
    "list_models": """List all available models on the VLLM server:

Server URL: {server_url}

Return a list of model names and their configurations.""",
}


class VLLMAgentPrompts:
    """Prompt templates for VLLM agent operations."""

    SYSTEM_PROMPT = VLLM_AGENT_SYSTEM_PROMPT
    PROMPTS = VLLM_AGENT_PROMPTS

    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the default system prompt."""
        return cls.SYSTEM_PROMPT

    @classmethod
    def get_prompt(cls, prompt_type: str, **kwargs) -> str:
        """Get a formatted prompt."""
        template = cls.PROMPTS.get(prompt_type, "")
        if not template:
            return ""

        try:
            return template.format(**kwargs)
        except KeyError as e:
            return f"Missing required parameter: {e}"
