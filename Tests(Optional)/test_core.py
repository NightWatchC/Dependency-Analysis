'''
This module contains tests for ./CodeAnalyzer/core_func.py
'''

# Standard library imports
from typing import Any, Dict, List, Optional
import sys, os
import tempfile
from pathlib import Path
from openai import OpenAI
import json
import re
import logging
import time
import unittest
import pytest
from pprint import pprint

# Tested module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import CodeAnalyzer.core_func as core_func

# Test Functions of File I/O Utilities
def e2e_test_scan_files():
    root_dir = input("Enter root directory path: ").strip()
    ext_text = input("Enter file extensions (comma-separated, e.g. .py,.md,.txt): ").strip()
    extensions = [e.strip() for e in ext_text.split(",") if e.strip()]

    result = core_func.scan_files(root_dir, extensions)

    print(f"\nFind {len(result)} files:")
    for p in result:
        print(p)

def e2e_test_read_file_content_manual():
    file_path = input("Enter file path to read: ").strip()
    content = core_func.read_file_content(file_path)

    if content is None:
        print("\nRead failed (function returned None)")
    else:
        print(f"\nRead successful, character count: {len(content)}")
        print("----- File Content -----")
        print(content[:])
        print("----- End of File Content -----")

def e2e_test_save_json():
    data = {
        "name": "Test Object",
        "value": 123,
        "items": [1, 2, 3],
        "nested": {"a": 1, "b": 2}
    }
    file_path = input("Enter file path to save JSON (e.g. output.json): ").strip()
    core_func.save_json(path = file_path, obj = data)
    print(f"\nData saved to {file_path}")

# Test Functions of LLM call and output processing Layer
def e2e_test_call_llm() -> None:
    '''Simple end-to-end test helper for manual verification.'''

    # Replace these values before running this file directly.
    api_key = ''
    base_url = 'https://api.deepseek.com/v1'
    model_name = 'deepseek-chat'

    prompt = 'What is 2 + 2?'

    result = core_func.call_llm(
        prompt=prompt,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        max_tokens=32,
        stream=False,
    )
    print("LLM Response:")
    print(result)

def e2e_test_extract_json_objects():
    text = '''
    Here is some text before the JSON.
    json
    {"key1": "value1", "key2": 123, "keyA": [1,2,3], "keyB": {"nestedKey": "nestedValue"}}
    and here is some text in between.
    json
    {"anotherKey": "anotherValue", "number": 456, "list": ["a", "b", "c"]}
    And some text after.
    '''
    json_objects = core_func.extract_json_object(text)
    print(f"Extracted {len(json_objects)} JSON objects:")
    for idx, obj in enumerate(json_objects, start=1):
        print(f"Object {idx}: {obj}")

# def unit_test_call_llm_json():

# Test Functions of JSON Parsing & Normalization
def e2e_test_to_unique_str_list():
    input_data = ["apple", "banana", "apple", "orange", "banana", 123, None, "grape"]
    result = core_func._to_unique_str_list(input_data)
    print(f"Input: {input_data}")
    print(f"Output: {result}")

# def unit_normalize_per_file_item():

# Test Functions of Analysis Pipeline
def e2e_analyze_one_file():
    file_path = input("Please enter file path file_path: ").strip()
    api_key = input("Please enter API Key: ").strip()
    base_url = input("Please enter base_url: ").strip()
    model_name = input("Please enter model_name (default deepseek-chat): ").strip() or "deepseek-chat"

    max_tokens_text = input("Please enter max_tokens: ").strip()
    retries_text = input("Please enter retries((default 2): ").strip()
    retry_delay_text = input("Please enter retry_delay(default 1.0): ").strip()

    max_tokens = int(max_tokens_text) if max_tokens_text else 1200
    retries = int(retries_text) if retries_text else 2
    retry_delay = float(retry_delay_text) if retry_delay_text else 1.0

    if not Path(file_path).exists():
        print(f"[错误] 文件不存在: {file_path}")
        return

    if not api_key or not base_url:
        print("[错误] API Key 和 base_url 不能为空")
        return

    print("\n开始调用 analyze_one_file...\n")
    result = core_func.analyze_one_file(
        file_path=file_path,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
        retries=retries,
        retry_delay=retry_delay,
    )

    print("调用完成，结果如下：")
    pprint(result, sort_dicts=False)

# def e2e_test_run_dependency_analysis():

# def e2e_test_build_fallback_dependency_report():

# Test
if __name__ == "__main__":
    print("Select test to run:")
    print("1. Test scan_files")
    print("2. Test read_file_content")
    print("3. Test save_json")
    print("4. Test call_llm (requires valid API key and base URL)")
    print("5. Test extract_json_objects")
    print("6. Test _to_unique_str_list")
    print("7. Test analyze_one_file (requires valid API key and base URL)")
    choice = input("Enter choice number: ").strip()

    if choice == "1":
        e2e_test_scan_files()
    elif choice == "2":
        e2e_test_read_file_content_manual()
    elif choice == "3":
        e2e_test_save_json()
    elif choice == "4":
        e2e_test_call_llm()
    elif choice == "5":
        e2e_test_extract_json_objects()
    elif choice == "6":
        e2e_test_to_unique_str_list()
    elif choice == "7":
        e2e_analyze_one_file()
    else:
        print("Invalid choice. Exiting.")
