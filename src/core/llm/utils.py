"""
Utility functions for the GitLab Agent System.
Contains helper functions for JSON extraction, text processing, and common operations.
"""

import re
import json
from typing import Optional, Dict, Any


def extract_json_block(text: str) -> Optional[Dict[Any, Any]]:
    """
    Extract and parse a JSON code block from text.
    Looks for ```json ... ``` blocks and parses them.
    Handles nested braces properly.
    
    Args:
        text: Text potentially containing JSON blocks
        
    Returns:
        Parsed JSON object or None if not found/invalid
    """
    if not text:
        return None
    
    # First try: Look for ```json blocks with optional PLAN label
    patterns = [
        r'```json\s+PLAN\s*(.*?)\s*```',  # ```json PLAN
        r'```json\s*(.*?)\s*```',         # ```json
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    # Second try: Find JSON with proper brace matching
    # This handles cases where the regex might cut off nested objects
    if '```json' in text:
        start_marker = text.find('```json')
        if start_marker != -1:
            # Find the opening brace after the marker
            json_start = text.find('{', start_marker)
            if json_start != -1:
                # Count braces to find matching closing brace
                brace_count = 0
                json_end = -1
                for i in range(json_start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i
                            break
                
                if json_end != -1:
                    try:
                        potential_json = text[json_start:json_end + 1]
                        return json.loads(potential_json)
                    except json.JSONDecodeError:
                        pass
    
    # Third try: Find raw JSON without code block markers
    json_start = text.find('{')
    if json_start != -1:
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False
        
        for i in range(json_start, len(text)):
            char = text[i]
            
            # Handle string literals to ignore braces inside strings
            if char == '"' and not escape_next:
                in_string = not in_string
            elif char == '\\' and not escape_next:
                escape_next = True
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i
                        break
            
            escape_next = False
        
        if json_end != -1:
            try:
                potential_json = text[json_start:json_end + 1]
                return json.loads(potential_json)
            except json.JSONDecodeError:
                pass
    
    return None


















