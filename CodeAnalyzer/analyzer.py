'''
This module contains the main logic for analyzing code and generating reports.
It uses core functions defined in core_func.py to perform file scanning(scan_files), content reading(read_file_content), and LLM interactions(call_llm).
'''

"""
requirements:
- openai>=1.0.0

Optional:
- python-dotenv (if you want to load env vars from .env manually)
"""
import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    # If run as package: python -m CodeAnalyzer.analyzer
    from . import core_func  # type: ignore
except Exception:
    # If run as script: python CodeAnalyzer/analyzer.py
    import core_func  # type: ignore

#change the scripts type to other languague types if needed, e.g. .py, .js, .java, etc.
STEP2_PROMPT_TEMPLATE = """You are analyzing an R/C++ script.
Return ONLY a JSON object with exactly these keys:
- "functions_called": list of strings
- "functions_defined": list of strings
- "datasets_read": list of strings
- "datasets_written": list of objects with keys:
  - "dataset_name": string
  - "operation": string
  - "object_written": string
  - "object_type": string or null

Rules:
- Do not include markdown.
- Do not include explanations.
- If uncertain, use best guess.
- If unknown, use empty list or null (for object_type).

Code:
{script_content}
"""

#change the scripts type to other languague types if needed, e.g. .py, .js, .java, etc.
STEP4_PROMPT_TEMPLATE = """I have a per-file JSON summary of R/C++ scripts.
Analyze it and return ONLY a JSON object with this schema:

{
  "dependencies": {
    "function_calls": [
      {"caller_script": "path/to/script1.R", "function": "funcA", "callee_script": "path/to/script2.R"}
    ],
    "dataset_flows": [
      {"producer_script": "path/to/script1.R", "dataset": "data.csv", "consumer_script": "path/to/script2.R"}
    ]
  },
  "dataset_structures": {
    "data.csv": "This dataset is inferred to at least have variable X(double),Y(string),Z() based on object_type and usage context."
  }
}

Task:
1) Identify inter-script function dependencies:
   - function defined in one script and called in another.
2) Identify dataset flows:
   - script writing dataset -> script reading same dataset.
3) Infer written dataset structures using object_type and usage context.

Input data:
{per_file_summary_json}
"""


def parse_args_formain() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze scripts and build dependency report via LLM."
    )
    parser.add_argument("root_dir", help="Root directory to scan recursively.")
    parser.add_argument("--file-type", default=".R,.cpp", help="Comma-separated file extensions to analyze (e.g. .R,.cpp)")
    parser.add_argument("--api-key")
    parser.add_argument(
        "--base-url"
    )
    parser.add_argument(
        "--model-name"
    )
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    parser.add_argument("--per-file-output")
    parser.add_argument("--dependency-output")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()

def main() -> int:
    args =  parse_args_formain()
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    root = Path(args.root_dir).resolve()
    if not root.exists() or not root.is_dir():
        logging.error("Invalid root directory: %s", root)
        return 1

    if not args.api_key:
        logging.error("Missing API key. Set --api-key or OPENAI_API_KEY.")
        return 1

    file_type = args.file_type
    extension = [ext.strip() for ext in file_type.split(",") if ext.strip()]
    files = core_func.scan_files(root_dir = str(root), extensions = extension)
    logging.info("Discovered %d target files under %s", len(files), root)

    per_file_summary: Dict[str, Dict[str, Any]] = {}

    for idx, file_path in enumerate(files, start=1):
        logging.info("Analyzing [%d/%d]: %s", idx, len(files), file_path)
        try:
            per_file_summary[file_path] = core_func.analyze_one_file(
                file_path=file_path,
                model_name=args.model_name,
                api_key=args.api_key,
                base_url=args.base_url,
                max_tokens=args.max_tokens,
                retries=args.retries,
                retry_delay=args.retry_delay,
            )
        except Exception as exc:
            logging.exception("Failed analyzing %s: %s", file_path, exc)
            per_file_summary[file_path] = {
                "functions_called": [],
                "functions_defined": [],
                "datasets_read": [],
                "datasets_written": [],
                "error": str(exc),
            }

    core_func.save_json(args.per_file_output, per_file_summary)
    logging.info("Saved per-file summary: %s", args.per_file_output)

    dependency_report = core_func.run_dependency_analysis(
        per_file_summary=per_file_summary,
        model_name=args.model_name,
        api_key=args.api_key,
        base_url=args.base_url,
        max_tokens=args.max_tokens,
        retries=args.retries,
        retry_delay=args.retry_delay,
    )

    core_func.save_json(args.dependency_output, dependency_report)
    logging.info("Saved dependency report: %s", args.dependency_output)
    return 0


if __name__ == "__main__":
    main()


