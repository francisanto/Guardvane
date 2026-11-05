"""
PromptShield AI — Cost Calculator.
=================================
Calculates input costs, estimated output costs, and total costs using dated public model pricing.
Input and output costs are strictly separated and labeled as estimates.
Safely handles unknown or missing pricing without fabricating zero-dollar figures.
"""

from dataclasses import dataclass
from typing import Optional
from analyzers.model_comparison.registry import ModelMetadata


@dataclass
class CostBreakdown:
    input_tokens: int
    estimated_output_tokens: int
    input_cost_usd: Optional[float]
    output_cost_usd: Optional[float]
    total_estimated_cost_usd: Optional[float]
    input_cost_per_m: Optional[float]
    output_cost_per_m: Optional[float]
    pricing_effective_date: str
    currency: str = "USD"
    pricing_status: str = "known"  # "known", "unknown"


def calculate_model_cost(
    model: ModelMetadata,
    input_tokens: int,
    estimated_output_tokens: int
) -> CostBreakdown:
    """
    Computes exact input cost and estimated output cost based on token counts and model pricing.
    If pricing is unverified, missing, or unknown, sets cost fields to None and marks pricing_status='unknown'.
    """
    p = model.pricing

    if not p.is_known or p.input_cost_per_m is None or p.output_cost_per_m is None:
        return CostBreakdown(
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            input_cost_usd=None,
            output_cost_usd=None,
            total_estimated_cost_usd=None,
            input_cost_per_m=None,
            output_cost_per_m=None,
            pricing_effective_date=p.pricing_effective_date,
            currency=p.currency,
            pricing_status="unknown"
        )

    input_cost = (input_tokens / 1_000_000.0) * p.input_cost_per_m
    output_cost = (estimated_output_tokens / 1_000_000.0) * p.output_cost_per_m
    total_cost = input_cost + output_cost

    return CostBreakdown(
        input_tokens=input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        input_cost_usd=round(input_cost, 6),
        output_cost_usd=round(output_cost, 6),
        total_estimated_cost_usd=round(total_cost, 6),
        input_cost_per_m=p.input_cost_per_m,
        output_cost_per_m=p.output_cost_per_m,
        pricing_effective_date=p.pricing_effective_date,
        currency=p.currency,
        pricing_status="known"
    )
