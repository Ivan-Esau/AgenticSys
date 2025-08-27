"""
Utility functions for the GitLab Agent System.
Contains helper functions for JSON extraction, text processing, and common operations.
"""

import re
import json
from typing import Optional, Dict, Any, List


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


def format_list_with_separator(items: List[str], separator: str = " | ") -> str:
    """
    Format a list of items with a separator.
    
    Args:
        items: List of items to format
        separator: Separator string (default: " | ")
        
    Returns:
        Formatted string
    """
    if not items:
        return ""
    return separator.join(items)


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with a suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def clean_branch_name(name: str) -> str:
    """
    Clean a string to be used as a valid Git branch name.
    
    Args:
        name: Raw branch name
        
    Returns:
        Cleaned branch name
    """
    # Replace invalid characters with hyphens
    cleaned = re.sub(r'[^a-zA-Z0-9\-_/]', '-', name)
    
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip('-')
    
    # Ensure it doesn't start with a slash
    cleaned = cleaned.lstrip('/')
    
    return cleaned or 'branch'


def format_timestamp(timestamp: str) -> str:
    """
    Format a timestamp for display.
    
    Args:
        timestamp: ISO format timestamp
        
    Returns:
        Formatted timestamp
    """
    # Remove microseconds for cleaner display
    if '.' in timestamp:
        timestamp = timestamp.split('.')[0]
    
    # Replace T with space for readability
    return timestamp.replace('T', ' ')


def parse_issue_references(text: str) -> List[str]:
    """
    Extract GitLab issue references from text.
    Looks for patterns like #123, !456, etc.
    
    Args:
        text: Text to parse
        
    Returns:
        List of issue references
    """
    # Match #123 (issues) and !456 (merge requests)
    pattern = r'[#!]\d+'
    matches = re.findall(pattern, text)
    
    return list(set(matches))  # Remove duplicates


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """
    Safely convert object to JSON string with error handling.
    
    Args:
        obj: Object to serialize
        indent: Indentation level
        
    Returns:
        JSON string or error message
    """
    try:
        return json.dumps(obj, indent=indent, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        return f"<Error serializing JSON: {e}>"


def extract_code_blocks(text: str, language: Optional[str] = None) -> List[str]:
    """
    Extract code blocks from markdown text.
    
    Args:
        text: Text containing code blocks
        language: Optional language filter (e.g., 'python', 'json')
        
    Returns:
        List of code block contents
    """
    if language:
        pattern = rf'```{language}\s*(.*?)\s*```'
    else:
        pattern = r'```(?:\w+)?\s*(.*?)\s*```'
    
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]


def split_into_chunks(text: str, chunk_size: int = 4000) -> List[str]:
    """
    Split text into chunks of specified size.
    Tries to split at sentence boundaries when possible.
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    current_chunk = ""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= chunk_size:
            current_chunk += (" " if current_chunk else "") + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        url: String to check
        
    Returns:
        True if valid URL, False otherwise
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(url_pattern.match(url))