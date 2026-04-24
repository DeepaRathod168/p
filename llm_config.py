"""
llm_config.py
─────────────
Centralised LLM configuration.

Supported providers (set LLM_PROVIDER in .env):
  • groq    – Groq cloud (llama3-70b)  [default]
  • openai  – OpenAI GPT-4o
  • ollama  – Local Ollama (no API key required)

Environment variables:
  LLM_PROVIDER      = groq | openai | ollama
  GROQ_API_KEY      = <key>        (groq)
  OPENAI_API_KEY    = <key>        (openai)
  OLLAMA_BASE_URL   = http://localhost:11434   (ollama, optional)
  OLLAMA_MODEL      = llama3       (ollama, optional)
"""

import os
import logging
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()
logger = logging.getLogger(__name__)


def get_llm() -> LLM:
    """
    Return a configured CrewAI LLM instance based on the LLM_PROVIDER env var.

    Returns
    -------
    LLM
        A ready-to-use CrewAI LLM object.

    Raises
    ------
    ValueError
        If required API keys are missing for the selected provider.
    """
    provider = os.getenv("LLM_PROVIDER", "groq").lower().strip()
    logger.info("LLM provider selected: %s", provider)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in the environment.")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        logger.info("Using OpenAI model: %s", model)
        return LLM(model=f"openai/{model}", api_key=api_key)

    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3")
        logger.info("Using Ollama model: %s at %s", model, base_url)
        return LLM(model=f"ollama/{model}", base_url=base_url)

    else:  # default → groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in the environment.")
        model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        logger.info("Using Groq model: %s", model)
        return LLM(model=f"groq/{model}", api_key=api_key)
