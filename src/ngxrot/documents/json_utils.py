"""Robust-but-honest JSON extraction from an LLM response. Tries a direct
parse first, then strips markdown code fences, then falls back to locating
the first balanced {...} block. Returns None (never a guessed/partial
structure) if nothing parses — a parse failure is a hard extraction
failure to be logged, not silently patched over.
"""

from __future__ import annotations

import json
import re


def parse_json_object(text: str) -> dict | None:
    text = text.strip()
    for candidate in (text, _strip_fences(text)):
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
    block = _first_balanced_object(text)
    if block is not None:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass
    return None


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return m.group(1) if m else text


def _first_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None
