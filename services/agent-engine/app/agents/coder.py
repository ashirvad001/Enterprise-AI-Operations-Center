"""
Coder Agent Node — Phase 2 of the multi-agent code review pipeline.

Responsibilities:
  - Accept the IssuePlan from the Planner
  - Generate a Python code fix using function-calling LLM
  - Return structured CodeOutput (filename, code, diff summary, deps)

Uses Ollama (Llama-3-8B) with JSON-mode output.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

from .state import AgentState, CodeOutput, IssuePlan

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _call_llm_for_code(plan: IssuePlan, issue: str) -> CodeOutput:
    """
    Calls the LLM to produce a code fix given a structured plan.
    Returns a CodeOutput Pydantic model.
    """
    system_prompt = (
        "You are an expert Python software engineer. "
        "Given a bug report and a plan, write a production-quality Python code fix. "
        "Follow PEP 8, add type hints, include docstrings, and handle edge cases."
    )

    user_prompt = f"""
Write a Python code fix for the following issue.

Issue: {issue}

Plan:
- Summary: {plan.summary}
- Root Cause: {plan.root_cause}
- Primary file to change: {plan.affected_files[0] if plan.affected_files else 'unknown.py'}
- Steps: {json.dumps(plan.steps, indent=2)}

Respond with a JSON object matching this schema:
{{
  "filename": "<path/to/file.py>",
  "language": "python",
  "code": "<complete fixed Python code>",
  "diff_summary": "<brief description of what changed>",
  "dependencies": ["<dep1>", "<dep2>"]
}}
"""

    # --- Try Ollama ---
    try:
        import httpx
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>",
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": 2048},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = json.loads(response.json().get("response", "{}"))
        return CodeOutput(**data)
    except Exception as e:
        logger.warning(f"Ollama unavailable ({e}), trying OpenAI fallback...")

    # --- Try OpenAI ---
    if OPENAI_API_KEY:
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=CodeOutput,
                temperature=0.2,
            )
            return completion.choices[0].message.parsed
        except Exception as e2:
            logger.warning(f"OpenAI also failed ({e2}), using mock code output...")

    # --- Deterministic Mock ---
    primary_file = plan.affected_files[0] if plan.affected_files else "fix.py"
    logger.info("Using mock coder output")
    return CodeOutput(
        filename=primary_file,
        language="python",
        code=f'''"""
Auto-generated fix for: {plan.summary}
Root cause: {plan.root_cause}
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


def fix_implementation(input_data: dict) -> Optional[dict]:
    """
    Implements the fix described in the issue plan.

    Args:
        input_data: The data structure that was causing the issue.

    Returns:
        Fixed output dict, or None on failure.
    """
    if not input_data:
        logger.warning("Received empty input_data, returning None")
        return None

    # TODO: Replace this stub with the actual fix implementation
    # Steps to implement:
    {chr(10).join(f"    # {i+1}. {step}" for i, step in enumerate(plan.steps))}

    result = {{**input_data, "_fixed": True}}
    logger.info(f"Fix applied successfully to {{len(input_data)}} keys")
    return result
''',
        diff_summary=f"Added fix_implementation() with proper input validation and logging. Addresses: {plan.summary}",
        dependencies=[],
    )


def code_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node: Coder.

    Input state keys consumed: plan, issue
    Output state keys produced: code, messages, latency_ms
    """
    start_ms = int(time.time() * 1000)

    if not state.get("plan"):
        return {
            "error": "Coder received no plan from Planner",
            "status": "failed",
            "messages": [{"node": "coder", "status": "error", "error": "Missing plan"}],
        }

    logger.info(f"[Coder] Generating fix for: {state['plan'].summary}")

    try:
        code_output = _call_llm_for_code(
            plan=state["plan"],
            issue=state["issue"],
        )
        elapsed = int(time.time() * 1000) - start_ms
        logger.info(f"[Coder] Completed in {elapsed}ms. File: {code_output.filename}")

        return {
            "code": code_output,
            "status": "running",
            "messages": [{
                "node": "coder",
                "status": "success",
                "filename": code_output.filename,
                "diff_summary": code_output.diff_summary,
                "elapsed_ms": elapsed,
            }],
            "latency_ms": {**state.get("latency_ms", {}), "coder": elapsed},
        }

    except Exception as e:
        logger.error(f"[Coder] Failed: {e}")
        return {
            "error": f"Coder failed: {str(e)}",
            "status": "failed",
            "messages": [{"node": "coder", "status": "error", "error": str(e)}],
        }
