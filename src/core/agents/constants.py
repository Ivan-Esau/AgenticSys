"""
Constants module for the GitLab Agent System.
Contains all prompts, messages, and constant values used across agents.
"""

# Agent Names
AGENT_NAMES = {
    "PLANNING": "planning-agent",
    "CODING": "coding-agent",
    "TESTING": "testing-agent",
    "REVIEW": "review-agent",
    "PIPELINE": "pipeline-agent",
    "ORCHESTRATOR": "orchestrator-agent",
    "UTILITY": "utility-agent"
}

# Status Messages
STATUS_MESSAGES = {
    "STARTING": "[>] Starting {agent_name}...",
    "COMPLETED": "[OK] {agent_name} completed successfully",
    "FAILED": "[FAIL] {agent_name} failed: {error}",
    "PROGRESS": "[...] {agent_name} in progress: {step}",
    "WAITING": "[WAIT] Waiting for {resource}...",
    "STREAMING_ERROR": "[WARN] Streaming error detected. Falling back to non-streaming mode.",
    "RETRY": "[RETRY] Retrying operation...",
    "NO_ISSUES": "[INFO] No open issues found in project"
}

# Error Messages
ERROR_MESSAGES = {
    "CONFIG_INVALID": "Invalid configuration. Please check your .env file.",
    "CONNECTION_FAILED": "Failed to connect to {service}",
    "TOOL_FAILED": "Tool execution failed: {tool_name}",
    "JSON_PARSE_ERROR": "Failed to parse JSON response",
    "NO_FINAL_MESSAGE": "No final message received from agent",
    "STREAM_INTERRUPTED": "Stream interrupted or connection broken"
}

# File and Branch Patterns
PATTERNS = {
    "BRANCH_PREFIX": "agent",
    "TIMESTAMP_FORMAT": "%Y%m%d-%H%M%S",
    "JSON_BLOCK": r'```json\s*(.*?)\s*```',
    "ISSUE_REFERENCE": r'[#!]\d+',
    "CODE_BLOCK": r'```(?:\w+)?\s*(.*?)\s*```'
}

# Limits and Thresholds
LIMITS = {
    "MAX_ISSUES": 100,
    "MAX_RETRIES": 3,
    "CHUNK_SIZE": 40000,
    "MAX_OUTPUT_LENGTH": 100000,
    "TRUNCATE_LENGTH": 10000,
    "STREAM_TIMEOUT": 30000  # seconds
}

# Default Values
DEFAULTS = {
    "BRANCH": "main",
    "TEMPERATURE": 0.0,
    "MODEL": "deepseek-chat",
    "HOST": "localhost",
    "PORT": "3333"
}

# Progress Indicators
PROGRESS_INDICATORS = {
    "TOOL_CALL": "[TOOL] Calling tool: {tool_name}",
    "TOKEN": "[MSG] Token: {token}",
    "CHUNK": "[CHUNK] Processing chunk {current}/{total}",
    "STEP": "[->] Step {step}: {description}"
}

# Agent Descriptions
AGENT_DESCRIPTIONS = {
    "PLANNING": "Analyzes project structure and creates development plans",
    "CODING": "Implements features and fixes based on issues",
    "TESTING": "Creates and manages test suites",
    "REVIEW": "Reviews code and manages merge requests",
    "PIPELINE": "Monitors CI/CD pipelines and handles failures",
    "ORCHESTRATOR": "Coordinates all agents and manages workflow"
}

# Emoji Indicators (ASCII alternatives for Windows compatibility)
EMOJIS = {
    "SUCCESS": "[OK]",
    "ERROR": "[ERR]",
    "WARNING": "[!]",
    "INFO": "[i]",
    "PROGRESS": "[...]",
    "ROCKET": "[>]",
    "TOOL": "[T]",
    "CHAT": "[M]",
    "CLOCK": "[W]",
    "DOCUMENT": "[D]",
    "PACKAGE": "[P]",
    "ARROW": "->",
    "CHECK": "[v]",
    "CROSS": "[x]",
    "ROBOT": "[A]"
}