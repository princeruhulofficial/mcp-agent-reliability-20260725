# Agent Reliability MCP

> Calculate how reliable your AI agent tool-chains really are — before you ship.

**One-liner**: Pure-math MCP server that tells you the real success probability of multi-step AI agents, finds the weakest tools, and suggests fixes. Zero external APIs, zero cost to run.

## Connect via MCPize

Use this MCP server instantly with no local installation:

```bash
npx -y mcpize connect @princeruhulofficial/agent-reliability --client claude
```

Or connect at: **https://mcpize.com/mcp/agent-reliability**

## Why this exists

AI agents look great in demos. In production a single 5% tool failure compounds into 40-60% overall failure after a few steps. This MCP lets any agent (or developer) ask:

- "If my tools succeed at 92%, 85%, 97% ... what is the real chance the whole chain finishes?"
- "Which tool is killing my reliability the most?"
- "What happens if I add 2 retries or a fallback?"

## Quick Start

```bash
# Install
pip install mcp numpy pydantic

# Run locally (stdio)
python -m src.server

# Or with mcpize later
mcpize run
```

## Tools

| Tool | What it does |
|------|--------------|
| `calculate_success_probability` | Overall success % for a list of tool rates |
| `find_bottleneck` | Rank tools by how much they hurt the chain |
| `suggest_improvements` | Actionable tips (retries, parallel, cache) with expected lift |
| `simulate_failure_scenarios` | Monte-Carlo view of 1000 runs |
| `estimate_cost_of_unreliability` | Rough $ or hours lost from failures |

## Example

```json
{
  "tools": [
    {"name": "search", "success_rate": 0.95},
    {"name": "summarize", "success_rate": 0.88},
    {"name": "write_file", "success_rate": 0.99}
  ]
}
```

→ Overall success ≈ 82.7%. Bottleneck = summarize. Add 1 retry on summarize → jumps to ~91%.

## Pricing (MCPize)

- Free: 50 calls/day
- Pro $19/mo: 500 calls/day + simulations
- Team $79/mo

## Built with

- Python + FastMCP style
- Pure computation (numpy optional)
- Ready for MCPize marketplace

## License

MIT

---

Daily AI MCP project by Grok for Prince Ruhul / Prevalid  
[![Available on MCPize](https://mcpize.com/badge/agent-reliability-mcp)](https://mcpize.com/servers/agent-reliability-mcp)