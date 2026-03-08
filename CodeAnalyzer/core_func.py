'''
This module provides core functions for the CodeAnalyzer tool, including LLM interaction and file scanning/reading utilities.
'''

# Standard library imports
from typing import Any, Dict, List, Optional
import os, sys
import tempfile
from pathlib import Path
from openai import OpenAI
import json
import re
import logging
import time

# import analyzer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import CodeAnalyzer.analyzer as analyzer

# Types & Constants
Message = Dict[str, str]

# File I/O Utilities
def scan_files(root_dir: str, extensions: List[str]) -> List[str]:
    """Recursively find all files with given extensions."""
    file_paths = []
    for foldername, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                full_path = os.path.join(foldername, filename)
                file_paths.append(full_path)
    return file_paths

def read_file_content(file_path: str) -> Optional[str]:
    """Read file content safely, return None if error."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return None

def save_json(path: str, obj: Any) -> None:
    """Save an object as JSON to the specified path."""
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved JSON to {path}")

# LLM call and output processing Layer
def call_llm(
    prompt: Optional[str],
    model_name: str,
    api_key: str,
    base_url: str,
    max_tokens: int,
    messages: Optional[List[Message]] = None,
    stream: bool = True,
    system_prompt: Optional[str] = None,
    client: Optional[OpenAI] = None,
    **kwargs: Any,
) -> str:
    '''Call an LLM and return text output.

    Backward compatible usage:
        call_llm(prompt, model_name, api_key, base_url, max_tokens)

    General usage:
        call_llm(
            prompt=None,
            model_name='gpt-4.1-mini',
            api_key='...',
            base_url='...',
            max_tokens=512,
            messages=[{'role': 'user', 'content': 'Hello'}],
            stream=False,
        )
    '''

    resolved_client = client or OpenAI(base_url=base_url, api_key=api_key)

    try:
        if messages is None:
            if prompt is None:
                raise ValueError('Either prompt or messages must be provided.')
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})

        response = resolved_client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0,
            stream=stream,
            **kwargs,
        )

        if stream:
            full_answer = ''
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_answer += chunk.choices[0].delta.content
            return full_answer.strip()

        # Non-streaming response.
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        return ''
    except Exception as e:
        prompt_preview = prompt if prompt is not None else '<messages mode>'
        print(f'Error calling LLM with prompt: {prompt_preview}')
        return f'Error calling LLM: {str(e)}'

import json
from typing import List, Dict, Any

def extract_json_object(text: str) -> List[Dict[str, Any]]:
    """Extract all JSON objects from text using raw_decode (supports nesting)."""
    content = text.strip()
    # optioanl: If the JSON is wrapped in a code fence, extract the content inside the fence first.
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
    if fence_match:
        content = fence_match.group(1).strip()

    decoder = json.JSONDecoder()
    objects = []
    idx = 0
    length = len(content)

    while idx < length:
        # skip whitespace to find the start of the next JSON object
        while idx < length and content[idx].isspace():
            idx += 1
        if idx >= length:
            break

        try:
            obj, end = decoder.raw_decode(content[idx:])
            objects.append(obj)
            idx += end  # move index to the end of the parsed JSON object
        except json.JSONDecodeError:
            # If the current character cannot start a valid JSON, move to the next character and try again
            idx += 1

    if not objects:
        raise ValueError("No valid JSON objects found.")
    return objects

# def call_llm_json(
#     prompt: str,
#     model_name: str,
#     api_key: str,
#     base_url: str,
#     max_tokens: int,
#     retries: int,
#     retry_delay: float,
# ) -> Dict[str, Any]:
#     '''Call LLM and parse JSON response, with retries on failure.'''
#     last_err: Optional[Exception] = None

#     for attempt in range(1, retries + 1):
#         try:
#             text = call_llm(
#                 prompt=prompt,
#                 model_name=model_name,
#                 api_key=api_key,
#                 base_url=base_url,
#                 max_tokens=max_tokens,
#                 stream=False,       # JSON parsing is easier with full response
#             )

#             if text.startswith("Error calling LLM:"):
#                 raise RuntimeError(text)

#             return extract_json_object(text)
#         except Exception as exc:
#             last_err = exc
#             logging.warning("LLM call failed (attempt %d/%d): %s", attempt, retries, exc)
#             if attempt < retries:
#                 time.sleep(retry_delay)

#     raise RuntimeError(f"LLM call failed after {retries} attempts: {last_err}")

def call_llm_json(
    prompt: str,
    model_name: str,
    api_key: str,
    base_url: str,
    max_tokens: int,
    retries: int,
    retry_delay: float,
) -> Dict[str, Any]:
    """Call LLM and parse a JSON object response, with retries on failure."""
    last_err: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            text = call_llm(
                prompt=prompt,
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                max_tokens=max_tokens,
                stream=False,  # JSON parsing is easier with full response
            )

            if text.startswith("Error calling LLM:"):
                raise RuntimeError(text)

            objs = extract_json_object(text)  # List of parsed JSON values
            dict_objs = [obj for obj in objs if isinstance(obj, dict)]

            if not dict_objs:
                raise ValueError("No JSON object (dict) found in LLM response.")
            if len(dict_objs) > 1:
                logging.warning(
                    "Multiple JSON objects found in LLM response; using the first one."
                )

            return dict_objs[0]
        except Exception as exc:
            last_err = exc
            logging.warning("LLM call failed (attempt %d/%d): %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(retry_delay)

    raise RuntimeError(f"LLM call failed after {retries} attempts: {last_err}")


# JSON Parsing & Normalization
def _to_unique_str_list(value: Any) -> List[str]:
    '''Convert a value to a list of unique, non-empty strings.'''
    if not isinstance(value, list):
        return []
    out: List[str] = []
    seen = set()
    for item in value:
        s = str(item).strip() if item is not None else ""
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out

def normalize_per_file_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    '''Normalize raw per-file analysis output into a consistent format.'''
    item: Dict[str, Any] = {
        "functions_called": _to_unique_str_list(raw.get("functions_called")),
        "functions_defined": _to_unique_str_list(raw.get("functions_defined")),
        "datasets_read": _to_unique_str_list(raw.get("datasets_read")),
        "datasets_written": [],
    }

    written = raw.get("datasets_written", [])
    if isinstance(written, list):
        for row in written:
            if not isinstance(row, dict):
                continue
            dataset_name = str(row.get("dataset_name", "")).strip()
            operation = str(row.get("operation", "")).strip()
            object_written = str(row.get("object_written", "")).strip()
            object_type = row.get("object_type", None)

            if isinstance(object_type, str):
                object_type = object_type.strip() or None
            elif object_type is not None:
                object_type = str(object_type).strip() or None

            if dataset_name or operation or object_written or object_type:
                item["datasets_written"].append(
                    {
                        "dataset_name": dataset_name,
                        "operation": operation,
                        "object_written": object_written,
                        "object_type": object_type,
                    }
                )

    return item

## Analysis Pipeline Helpers
def analyze_one_file(
    file_path: str,
    model_name: str,
    api_key: str,
    base_url: str,
    max_tokens: int,
    retries: int,
    retry_delay: float,
) -> Dict[str, Any]:
    '''Analyze a single file and return normalized results.'''
    content = read_file_content(file_path)
    if content is None:
        raise RuntimeError("Failed to read file content.")

    prompt = analyzer.STEP2_PROMPT_TEMPLATE.format(script_content=content)
    raw = call_llm_json(
        prompt=prompt,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
        retries=retries,
        retry_delay=retry_delay,
    )
    return normalize_per_file_item(raw)

def run_dependency_analysis(
    per_file_summary: Dict[str, Dict[str, Any]],
    model_name: str,
    api_key: str,
    base_url: str,
    max_tokens: int,
    retries: int,
    retry_delay: float,
) -> Dict[str, Any]:
    ''''Run Step-4 dependency analysis using the per-file summary as input.'''
    payload = json.dumps(per_file_summary, ensure_ascii=False, indent=2)
    prompt = analyzer.STEP4_PROMPT_TEMPLATE.replace("{per_file_summary_json}", payload)

    try:
        result = call_llm_json(
            prompt=prompt,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            max_tokens=max_tokens,
            retries=retries,
            retry_delay=retry_delay,
        )
        # Light schema guard
        if not isinstance(result, dict) or "dependencies" not in result or "dataset_structures" not in result:
            raise ValueError("Step-4 response missing required top-level keys.")
        return result
    except Exception as exc:
        logging.warning("Step-4 LLM analysis failed, using fallback logic: %s", exc)
        return build_fallback_dependency_report(per_file_summary)

def build_fallback_dependency_report(per_file_summary: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    '''Build a dependency report using deterministic logic based on the per-file summary.'''
    # Local deterministic fallback if step-4 LLM fails.
    func_defined_to_scripts: Dict[str, List[str]] = {}
    producers: Dict[str, List[str]] = {}
    dataset_structures: Dict[str, str] = {}

    for script, info in per_file_summary.items():
        for fn in info.get("functions_defined", []):
            func_defined_to_scripts.setdefault(fn, []).append(script)

        for row in info.get("datasets_written", []):
            dataset = (row.get("dataset_name") or "").strip()
            if dataset:
                producers.setdefault(dataset, []).append(script)

                obj_type = row.get("object_type")
                obj_written = row.get("object_written") or "unknown_object"
                operation = row.get("operation") or "unknown_operation"
                if dataset not in dataset_structures:
                    if obj_type:
                        dataset_structures[dataset] = (
                            f"inferred {obj_type} written from '{obj_written}' via {operation}"
                        )
                    else:
                        dataset_structures[dataset] = (
                            f"written from '{obj_written}' via {operation}; type uncertain"
                        )

    function_calls: List[Dict[str, str]] = []
    for caller_script, info in per_file_summary.items():
        for called in info.get("functions_called", []):
            for callee_script in func_defined_to_scripts.get(called, []):
                if callee_script != caller_script:
                    function_calls.append(
                        {
                            "caller_script": caller_script,
                            "function": called,
                            "callee_script": callee_script,
                        }
                    )

    dataset_flows: List[Dict[str, str]] = []
    for consumer_script, info in per_file_summary.items():
        for dataset in info.get("datasets_read", []):
            for producer_script in producers.get(dataset, []):
                if producer_script != consumer_script:
                    dataset_flows.append(
                        {
                            "producer_script": producer_script,
                            "dataset": dataset,
                            "consumer_script": consumer_script,
                        }
                    )

    return {
        "dependencies": {
            "function_calls": function_calls,
            "dataset_flows": dataset_flows,
        },
        "dataset_structures": dataset_structures,
    }

