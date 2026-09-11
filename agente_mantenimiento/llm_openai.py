from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .config import PROJECT_DIR
from .database import HistoryDatabase
from .economics import MODEL_PRICES, PRICING_EFFECTIVE_DATE, calculate_cost
from .llm_contract import build_llm_context, validate_llm_payload


class LLMServiceError(RuntimeError):
    """Raised when the external interpretation service cannot finish safely."""


FINDINGS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "findings": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "relation_type": {"type": "string", "enum": ["same_bridge", "cross_bridge"]},
                    "title": {"type": "string"},
                    "notice_numbers": {
                        "type": "array", "minItems": 2, "items": {"type": "string"}
                    },
                    "confidence": {"type": "string", "enum": ["baja", "media", "alta"]},
                    "rationale": {"type": "string"},
                    "human_review": {"type": "string"},
                },
                "required": [
                    "relation_type", "title", "notice_numbers", "confidence",
                    "rationale", "human_review",
                ],
            },
        }
    },
    "required": ["findings"],
}


SYSTEM_PROMPT_PATH = PROJECT_DIR / "prompts" / "system_prompt.md"
INSTRUCTIONS = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _call_responses_api(body: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:800]
        raise LLMServiceError(f"OpenAI devolvió HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise LLMServiceError(f"No se pudo completar la interpretación LLM: {error}") from error


def _output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    if not parts:
        raise LLMServiceError("La respuesta del LLM no contiene texto estructurado utilizable.")
    return "".join(parts)


def interpret_week_with_openai(
    database_path: str | Path,
    *,
    year: int,
    week: int,
    api_key: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    transport: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
) -> int:
    """Interpret stored facts, validate the response, then save it for one report week."""
    key = api_key or os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise LLMServiceError(
            "Falta OPENAI_API_KEY. Los cálculos se guardaron, pero la corrida está incompleta."
        )
    database = HistoryDatabase(database_path)
    if not database.week_exists(year, week):
        raise LLMServiceError(f"La semana {week}/{year} no existe en la base.")
    context = build_llm_context(database_path, year=year, week=week)
    selected_model = model or os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    selected_effort = reasoning_effort or os.environ.get("OPENAI_REASONING_EFFORT", "medium")
    body = {
        "model": selected_model,
        "reasoning": {"effort": selected_effort},
        "instructions": INSTRUCTIONS,
        "input": json.dumps(context, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema", "name": "maintenance_findings",
                "strict": True, "schema": FINDINGS_SCHEMA,
            }
        },
        "store": False,
    }
    response = (transport or _call_responses_api)(body, key)
    try:
        payload = json.loads(_output_text(response))
    except json.JSONDecodeError as error:
        raise LLMServiceError("El LLM no devolvió JSON válido.") from error
    validated = validate_llm_payload(database_path, payload, year=year, week=week)
    if not validated:
        raise LLMServiceError(
            "El LLM no produjo hallazgos. La corrida permanece incompleta para revisión."
        )
    count = database.replace_llm_findings(validated, year=year, week=week)
    usage = response.get("usage") or {}
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    cached_tokens = int(input_details.get("cached_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    costs = calculate_cost(
        selected_model, input_tokens=input_tokens, cached_input_tokens=cached_tokens,
        output_tokens=output_tokens,
    )
    price = MODEL_PRICES.get(selected_model)
    database.save_llm_run({
        "report_year": year, "report_week": week, "model": selected_model,
        "reasoning_effort": selected_effort, "response_id": str(response.get("id") or ""),
        "input_tokens": input_tokens, "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": int(output_details.get("reasoning_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or input_tokens + output_tokens),
        **costs,
        "price_input_per_million": price.input_per_million if price else None,
        "price_cached_input_per_million": price.cached_input_per_million if price else None,
        "price_output_per_million": price.output_per_million if price else None,
        "pricing_effective_date": PRICING_EFFECTIVE_DATE,
    })
    return count
