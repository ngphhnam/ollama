"""JSON extraction utilities from LLM responses"""
import json
import re
from typing import Dict


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response"""
    # Try to find JSON in the response
    json_match = re.search(r'\{[^{}]*"bandScore"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # Try to parse entire response as JSON
    try:
        return json.loads(text)
    except:
        pass
    
    # Fallback: try to extract values using regex
    result = {}
    patterns = {
        "bandScore": r'"bandScore"\s*:\s*([0-9.]+)',
        "pronunciationScore": r'"pronunciationScore"\s*:\s*([0-9.]+)',
        "grammarScore": r'"grammarScore"\s*:\s*([0-9.]+)',
        "vocabularyScore": r'"vocabularyScore"\s*:\s*([0-9.]+)',
        "fluencyScore": r'"fluencyScore"\s*:\s*([0-9.]+)',
        "overallFeedback": r'"overallFeedback"\s*:\s*"([^"]+)"'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            if key == "overallFeedback":
                result[key] = match.group(1)
            else:
                result[key] = float(match.group(1))
    
    return result


def extract_json_from_generate_response(response_text: str) -> dict:
    """Extract JSON from generation response (more flexible parsing)"""
    if not response_text or not isinstance(response_text, str):
        return {"content": str(response_text) if response_text else ""}
    
    # Clean the response text
    response_text = response_text.strip()
    
    # Try to parse as JSON directly
    try:
        result = json.loads(response_text)
        
        # If result is a dict with only "content" key and content is a JSON string, parse it
        if isinstance(result, dict) and len(result) == 1 and "content" in result:
            content_value = result["content"]
            if isinstance(content_value, str):
                try:
                    # Try to parse the content as JSON
                    parsed_content = json.loads(content_value)
                    if isinstance(parsed_content, dict):
                        result = parsed_content
                except:
                    pass  # Keep original result if parsing fails
        
        return result
        
    except json.JSONDecodeError:
        # JSON parsing failed, try to extract JSON from text
        pass
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            return result
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in text (improved regex to handle nested objects)
    # Find the first { and match until the last } with balanced braces
    brace_count = 0
    start_idx = response_text.find('{')
    if start_idx >= 0:
        for i in range(start_idx, len(response_text)):
            if response_text[i] == '{':
                brace_count += 1
            elif response_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found complete JSON object
                    json_str = response_text[start_idx:i+1]
                    try:
                        result = json.loads(json_str)
                        return result
                    except json.JSONDecodeError:
                        # Try to fix common JSON issues
                        # Remove trailing commas
                        json_str = re.sub(r',\s*}', '}', json_str)
                        json_str = re.sub(r',\s*]', ']', json_str)
                        try:
                            result = json.loads(json_str)
                            return result
                        except:
                            pass
                    break
    
    # Try simple regex as fallback
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(0))
            return result
        except json.JSONDecodeError:
            pass
    
    # Try to extract multiple JSON objects (in case response contains multiple vocabulary items)
    # This handles cases where Google AI returns multiple separate JSON objects
    json_objects = []
    start_idx = 0
    while start_idx < len(response_text):
        brace_count = 0
        obj_start = response_text.find('{', start_idx)
        if obj_start < 0:
            break
        
        for i in range(obj_start, len(response_text)):
            if response_text[i] == '{':
                brace_count += 1
            elif response_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = response_text[obj_start:i+1]
                    try:
                        obj = json.loads(json_str)
                        json_objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    start_idx = i + 1
                    break
        else:
            break
    
    # If we found multiple JSON objects, try to combine them
    if len(json_objects) > 1:
        # Check if they're all vocabulary items
        if all(isinstance(obj, dict) and all(key in obj for key in ["word", "definition", "example"]) for obj in json_objects):
            return {"vocabulary": json_objects}
        # Otherwise return as list
        return json_objects[0] if len(json_objects) == 1 else {"items": json_objects}
    elif len(json_objects) == 1:
        return json_objects[0]
    
    # If all parsing fails, return content as text with error info
    return {
        "content": response_text,
        "_parse_error": "Could not extract JSON from response",
        "_response_preview": response_text[:500] if len(response_text) > 500 else response_text
    }

