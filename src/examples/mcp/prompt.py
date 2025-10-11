#!/usr/bin/env python3
"""
Prompts and helper utilities for the MCP transport connectivity demo.
"""

# System prompt describing available MCP tools
MCP_SYSTEM_PROMPT = """You are a helpful assistant with access to the Everything MCP Server tools.

The Everything MCP Server provides these basic tools:
- echo: Echo back input messages
- add: Add two numbers together

Always invoke the MCP tools when they are appropriate. Explain what you are doing."""

# Welcome banner for the CLI demo
WELCOME_MESSAGE = """
🌟 Everything MCP Server Demo - Transport Connectivity
=====================================================

This demo showcases MCP transport connectivity using basic tools:
1. Stdio Transport - Direct process communication
2. HTTP Transport - HTTP connections

Each transport will demonstrate:
- Connection establishment and tool discovery
- Basic echo functionality to verify connectivity
- Simple math operations to test tool execution
"""

# Test scenarios for the demo
TEST_SCENARIOS = {
    "connectivity": {
        "name": "Connectivity Test",
        "prompt": "Use the echo tool to say 'Connected successfully!' to verify the transport is working."
    },
    "basic_math": {
        "name": "Basic Math Operation",
        "prompt": "Use the add tool to calculate 15 + 27 to test tool execution."
    }
}


def get_demo_prompt(scenario: str) -> str:
    """Return the natural-language prompt for a given scenario key."""
    if scenario not in TEST_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}. Available keys: {list(TEST_SCENARIOS)}")
    return TEST_SCENARIOS[scenario]["prompt"]


def get_scenario_name(scenario: str) -> str:
    """Return the display name for the scenario."""
    if scenario not in TEST_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}. Available keys: {list(TEST_SCENARIOS)}")
    return TEST_SCENARIOS[scenario]["name"]


def format_demo_output(transport: str, scenario: str, response: str, truncate: int = 600) -> str:
    """Format the demo output for display in the CLI."""
    scenario_name = get_scenario_name(scenario)
    truncated = response[:truncate] + ("..." if len(response) > truncate else "")

    return f"""
📋 {transport.upper()} Transport - {scenario_name}
{'-' * (len(transport) + len(scenario_name) + 15)}
Response: {truncated}
"""
