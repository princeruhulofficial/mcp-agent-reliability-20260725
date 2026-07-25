"""
Agent Reliability MCP Server
Pure-computation tools to predict and improve multi-step AI agent success rates.
"""

from __future__ import annotations

import math
import random
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, confloat

mcp = FastMCP(
    "agent-reliability-mcp",
    description="Calculate success probability and bottlenecks for AI agent tool chains",
)


class ToolRate(BaseModel):
    name: str = Field(..., description="Name of the tool or step")
    success_rate: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Probability this tool succeeds (0.0 to 1.0)"
    )
    retries: int = Field(0, ge=0, le=5, description="Number of automatic retries already configured")


class ChainInput(BaseModel):
    tools: list[ToolRate] = Field(..., min_length=1, description="Ordered list of tools in the chain")
    independent: bool = Field(True, description="Assume failures are independent")


def _effective_rate(rate: float, retries: int) -> float:
    """Probability of success after N retries (at least one success)."""
    if retries <= 0:
        return rate
    fail = 1.0 - rate
    return 1.0 - (fail ** (retries + 1))


def _overall_probability(tools: list[ToolRate]) -> float:
    p = 1.0
    for t in tools:
        p *= _effective_rate(t.success_rate, t.retries)
    return p


@mcp.tool()
def calculate_success_probability(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate the overall success probability of a multi-step agent tool chain.
    Each tool has a success_rate (0-1) and optional retries.
    Returns overall probability and a simple confidence note.
    """
    chain = ChainInput(tools=[ToolRate(**t) for t in tools])
    overall = _overall_probability(chain.tools)
    n = len(chain.tools)
    # Simple confidence: lower when more steps
    confidence = max(0.5, 1.0 - (n * 0.03))

    return {
        "overall_success_probability": round(overall, 4),
        "percentage": f"{overall * 100:.1f}%",
        "steps": n,
        "confidence": round(confidence, 2),
        "note": "Assumes independent failures. Real systems may have correlated errors.",
        "tools_used": [
            {
                "name": t.name,
                "base_rate": t.success_rate,
                "retries": t.retries,
                "effective_rate": round(_effective_rate(t.success_rate, t.retries), 4),
            }
            for t in chain.tools
        ],
    }


@mcp.tool()
def find_bottleneck(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Rank every tool by how much it hurts the overall success probability.
    The top item is the biggest bottleneck.
    """
    chain = ChainInput(tools=[ToolRate(**t) for t in tools])
    base = _overall_probability(chain.tools)

    impacts = []
    for i, t in enumerate(chain.tools):
        # What if this tool was perfect (rate=1.0)?
        perfect_tools = [
            ToolRate(name=x.name, success_rate=1.0 if j == i else x.success_rate, retries=x.retries)
            for j, x in enumerate(chain.tools)
        ]
        perfect_p = _overall_probability(perfect_tools)
        impact = perfect_p - base
        impacts.append(
            {
                "name": t.name,
                "current_effective": round(_effective_rate(t.success_rate, t.retries), 4),
                "impact_if_perfect": round(impact, 4),
                "rank_score": impact,
            }
        )

    impacts.sort(key=lambda x: x["rank_score"], reverse=True)
    for idx, item in enumerate(impacts):
        item["rank"] = idx + 1
        del item["rank_score"]

    return {
        "current_overall": round(base, 4),
        "bottlenecks": impacts,
        "top_bottleneck": impacts[0]["name"] if impacts else None,
        "advice": f"Focus first on improving '{impacts[0]['name']}' — it gives the biggest lift.",
    }


@mcp.tool()
def suggest_improvements(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Suggest concrete improvements (add retries, parallelize, add fallback) 
    and estimate the new success probability for each suggestion.
    """
    chain = ChainInput(tools=[ToolRate(**t) for t in tools])
    base = _overall_probability(chain.tools)
    suggestions = []

    # Suggestion 1: add 1 retry to the weakest tool
    weakest = min(chain.tools, key=lambda t: _effective_rate(t.success_rate, t.retries))
    improved = [
        ToolRate(
            name=t.name,
            success_rate=t.success_rate,
            retries=t.retries + 1 if t.name == weakest.name else t.retries,
        )
        for t in chain.tools
    ]
    new_p = _overall_probability(improved)
    suggestions.append(
        {
            "action": f"Add 1 retry to '{weakest.name}'",
            "expected_new_probability": round(new_p, 4),
            "lift": round(new_p - base, 4),
            "effort": "Low (config change)",
        }
    )

    # Suggestion 2: make two weakest parallel (conceptual)
    if len(chain.tools) >= 2:
        sorted_weak = sorted(chain.tools, key=lambda t: _effective_rate(t.success_rate, t.retries))
        a, b = sorted_weak[0], sorted_weak[1]
        # Parallel success = 1 - fail_a * fail_b
        parallel_rate = 1 - (1 - _effective_rate(a.success_rate, a.retries)) * (
            1 - _effective_rate(b.success_rate, b.retries)
        )
        # Rough: replace the two with one parallel step
        rest = [t for t in chain.tools if t.name not in (a.name, b.name)]
        parallel_chain = rest + [
            ToolRate(name=f"{a.name}+{b.name}_parallel", success_rate=parallel_rate, retries=0)
        ]
        new_p2 = _overall_probability(parallel_chain)
        suggestions.append(
            {
                "action": f"Run '{a.name}' and '{b.name}' in parallel (if possible)",
                "expected_new_probability": round(new_p2, 4),
                "lift": round(new_p2 - base, 4),
                "effort": "Medium (workflow change)",
            }
        )

    # Suggestion 3: raise weakest to 0.95
    raised = [
        ToolRate(
            name=t.name,
            success_rate=0.95 if t.name == weakest.name else t.success_rate,
            retries=t.retries,
        )
        for t in chain.tools
    ]
    new_p3 = _overall_probability(raised)
    suggestions.append(
        {
            "action": f"Improve '{weakest.name}' reliability to 95% (better prompt, schema, or provider)",
            "expected_new_probability": round(new_p3, 4),
            "lift": round(new_p3 - base, 4),
            "effort": "High (engineering)",
        }
    )

    suggestions.sort(key=lambda s: s["lift"], reverse=True)

    return {
        "current_probability": round(base, 4),
        "suggestions": suggestions,
        "best_quick_win": suggestions[0] if suggestions else None,
    }


@mcp.tool()
def simulate_failure_scenarios(
    tools: list[dict[str, Any]], num_simulations: int = 1000
) -> dict[str, Any]:
    """
    Run a simple Monte-Carlo simulation of the tool chain.
    Shows how often the whole chain succeeds and common failure points.
    """
    chain = ChainInput(tools=[ToolRate(**t) for t in tools])
    n_sim = min(max(num_simulations, 100), 5000)

    successes = 0
    fail_counts: dict[str, int] = {t.name: 0 for t in chain.tools}

    for _ in range(n_sim):
        failed = False
        for t in chain.tools:
            eff = _effective_rate(t.success_rate, t.retries)
            if random.random() > eff:
                fail_counts[t.name] += 1
                failed = True
                break  # chain stops at first failure
        if not failed:
            successes += 1

    return {
        "simulations": n_sim,
        "success_count": successes,
        "success_rate": round(successes / n_sim, 4),
        "failure_by_tool": {
            k: {"count": v, "pct_of_failures": round(v / max(1, n_sim - successes) * 100, 1)}
            for k, v in fail_counts.items()
        },
        "note": "Simulation stops at first failure (sequential chain). Real agents may continue or retry differently.",
    }


@mcp.tool()
def estimate_cost_of_unreliability(
    tools: list[dict[str, Any]],
    daily_runs: int = 100,
    cost_per_failure_usd: float = 2.0,
) -> dict[str, Any]:
    """
    Rough estimate of monthly money or time lost because the agent fails.
    Useful for business case / prioritization.
    """
    chain = ChainInput(tools=[ToolRate(**t) for t in tools])
    p = _overall_probability(chain.tools)
    failure_rate = 1.0 - p
    daily_failures = daily_runs * failure_rate
    monthly_failures = daily_failures * 30
    monthly_cost = monthly_failures * cost_per_failure_usd

    return {
        "overall_success_probability": round(p, 4),
        "failure_rate": round(failure_rate, 4),
        "daily_runs": daily_runs,
        "estimated_daily_failures": round(daily_failures, 1),
        "estimated_monthly_failures": round(monthly_failures, 0),
        "cost_per_failure_usd": cost_per_failure_usd,
        "estimated_monthly_cost_usd": round(monthly_cost, 2),
        "note": "This is a simple linear estimate. Real cost may include support tickets, lost users, or brand damage.",
    }


if __name__ == "__main__":
    mcp.run()
