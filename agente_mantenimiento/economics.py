from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


PRICING_SOURCE = "https://developers.openai.com/api/docs/models"
PRICING_EFFECTIVE_DATE = "2026-09-08"


@dataclass(frozen=True)
class ModelPrice:
    label: str
    input_per_million: float
    cached_input_per_million: float
    output_per_million: float


MODEL_PRICES: dict[str, ModelPrice] = {
    "gpt-5.4": ModelPrice("GPT-5.4", 2.50, 0.25, 15.00),
    "gpt-5.4-mini": ModelPrice("GPT-5.4 Mini", 0.75, 0.075, 4.50),
    "gpt-5.4-nano": ModelPrice("GPT-5.4 Nano", 0.20, 0.02, 1.25),
}

REASONING_EFFORTS = ("none", "low", "medium", "high", "xhigh")


def calculate_cost(
    model: str, *, input_tokens: int, cached_input_tokens: int, output_tokens: int
) -> dict[str, float]:
    price = MODEL_PRICES.get(model)
    if price is None:
        return {"input_cost_usd": 0.0, "cached_input_cost_usd": 0.0,
                "output_cost_usd": 0.0, "total_cost_usd": 0.0}
    cached = max(0, min(cached_input_tokens, input_tokens))
    uncached = max(0, input_tokens - cached)
    input_cost = uncached * price.input_per_million / 1_000_000
    cached_cost = cached * price.cached_input_per_million / 1_000_000
    output_cost = max(0, output_tokens) * price.output_per_million / 1_000_000
    return {
        "input_cost_usd": input_cost,
        "cached_input_cost_usd": cached_cost,
        "output_cost_usd": output_cost,
        "total_cost_usd": input_cost + cached_cost + output_cost,
    }


def estimate_text_tokens(value: Any) -> int:
    """Transparent planning estimate. API usage remains the billing source of truth."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return max(1, round(len(text) / 4))


def comparison_rows(input_tokens: int, output_tokens: int) -> list[dict[str, Any]]:
    rows = []
    baseline = calculate_cost(
        "gpt-5.4", input_tokens=input_tokens, cached_input_tokens=0,
        output_tokens=output_tokens,
    )["total_cost_usd"]
    for model, price in MODEL_PRICES.items():
        cost = calculate_cost(
            model, input_tokens=input_tokens, cached_input_tokens=0,
            output_tokens=output_tokens,
        )["total_cost_usd"]
        for effort in REASONING_EFFORTS:
            rows.append({
                "model": model, "label": price.label, "reasoning_effort": effort,
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "estimated_cost_usd": cost,
                "savings_vs_gpt54_usd": baseline - cost,
                "savings_vs_gpt54_percent": 0.0 if not baseline else (baseline - cost) / baseline * 100,
            })
    return rows
