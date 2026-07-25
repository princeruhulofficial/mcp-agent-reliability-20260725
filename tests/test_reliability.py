"""Basic unit tests for agent-reliability-mcp"""

import sys
sys.path.insert(0, "src")

from server import (
    _effective_rate,
    _overall_probability,
    ToolRate,
    calculate_success_probability,
    find_bottleneck,
)


def test_effective_rate_no_retry():
    assert _effective_rate(0.9, 0) == 0.9


def test_effective_rate_with_retries():
    # 0.8 with 1 retry = 1 - 0.2*0.2 = 0.96
    assert abs(_effective_rate(0.8, 1) - 0.96) < 1e-6


def test_overall_simple():
    tools = [
        ToolRate(name="a", success_rate=0.9, retries=0),
        ToolRate(name="b", success_rate=0.9, retries=0),
    ]
    assert abs(_overall_probability(tools) - 0.81) < 1e-6


def test_calculate_tool():
    result = calculate_success_probability(
        [{"name": "search", "success_rate": 0.95}, {"name": "write", "success_rate": 0.99}]
    )
    assert "overall_success_probability" in result
    assert result["overall_success_probability"] > 0.9


def test_find_bottleneck():
    result = find_bottleneck(
        [
            {"name": "strong", "success_rate": 0.99},
            {"name": "weak", "success_rate": 0.7},
            {"name": "ok", "success_rate": 0.95},
        ]
    )
    assert result["top_bottleneck"] == "weak"
    assert result["bottlenecks"][0]["name"] == "weak"


if __name__ == "__main__":
    test_effective_rate_no_retry()
    test_effective_rate_with_retries()
    test_overall_simple()
    test_calculate_tool()
    test_find_bottleneck()
    print("All tests passed!")
