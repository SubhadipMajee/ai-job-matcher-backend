"""
ai_client.py — Centralized Groq LLM client, model selector, and robust JSON parser.
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Select model: default to openai/gpt-oss-120b (available on Groq)
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
FALLBACK_MODEL = "openai/gpt-oss-20b"

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_completion(messages: list[dict], temperature: float = 0.2) -> str:
    """
    Get chat completion from Groq with automatic fallback to secondary model.
    """
    try:
        resp = groq_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        # Fallback to secondary model if primary encounters an error
        try:
            resp = groq_client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception:
            raise exc


def parse_json_safely(raw: str, default=None):
    """
    Safely extract and parse JSON from LLM output, stripping markdown backticks if present.
    """
    if not raw:
        return default
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        try:
            return eval(text)
        except Exception:
            return default
