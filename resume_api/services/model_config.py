"""
Central model configuration for the knowledge graph API.

This is the SINGLE source of truth for the default LLM model.
To change the model used across the entire application, edit
DEFAULT_MODEL below — no other file needs to be modified.
"""

# The default model used for all LLM calls
DEFAULT_MODEL = "openai/gpt-oss-20b:free"