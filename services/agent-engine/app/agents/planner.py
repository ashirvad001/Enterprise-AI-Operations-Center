"""
Planner Agent Node — Phase 1 of the multi-agent code review pipeline.

Responsibilities:
  - Parse the GitHub issue description
  - Identify root cause, affected files, and complexity
  - Produce a structured IssuePlan via LLM function-calling

LLM Backend: Ollama (Llama-3-8B) with structured output via Pydantic schema.
Swap OLLAMA_BASE_URL to point at cloud LLM by changing settings.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

from .state import AgentState, IssuePlan

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ---------------------------------------------------------------------------
# LLM Caller (supports Ollama + OpenAI fallback)
# ---------------------------------------------------------------------------

def _call_llm_for_plan(issue: str, issue_id: str, repository: str) -> IssuePlan:
    """
    Calls the configured LLM and returns a structured IssuePlan.

    Tries Ollama first; falls back to OpenAI if OPENAI_API_KEY is set
    and Ollama is unavailable.
    """
    system_prompt = (
        "You are a senior software engineer and architect. "
        "Your job is to analyze GitHub issues and produce a precise, "
        "structured plan to resolve them. Be specific about which files "
        "need to change and what the root cause is."
    )

    user_prompt = f"""
Analyze the following GitHub issue and create a detailed resolution plan.

Repository: {repository}
Issue ID: {issue_id}
Issue Description:
---
{issue}
---

Respond with a JSON object matching this exact schema:
{{
  "issue_id": "{issue_id}",
  "summary": "<one sentence summary>",
  "root_cause": "<suspected root cause>",
  "affected_files": ["<file1>", "<file2>"],
  "steps": ["<step 1>", "<step 2>", "<step 3>"],
  "complexity": "<low|medium|high>"
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
                "options": {"temperature": 0.1, "num_ctx": 4096},
            },
            timeout=60.0,
        )
        response.raise_for_status()
        raw = response.json().get("response", "{}")
        data = json.loads(raw)
        return IssuePlan(**data)
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
                response_format=IssuePlan,
                temperature=0.1,
            )
            return completion.choices[0].message.parsed
        except Exception as e2:
            logger.warning(f"OpenAI also failed ({e2}), using deterministic mock...")

    # --- Deterministic Mock (always works, useful for tests) ---
    logger.info("Using mock planner output (no LLM available)")
    return IssuePlan(
        issue_id=issue_id,
        summary=f"Mock plan for issue: {issue[:60]}...",
        root_cause="Unable to determine root cause without LLM. Please configure OLLAMA_BASE_URL or OPENAI_API_KEY.",
        affected_files=["src/main.py", "tests/test_main.py"],
        steps=[
            "1. Reproduce the issue locally",
            "2. Add failing test case",
            "3. Fix the root cause",
            "4. Verify all tests pass",
            "5. Submit PR with documentation",
        ],
        complexity="medium",
    )


# ---------------------------------------------------------------------------
# LangGraph Node Function
# ---------------------------------------------------------------------------

def plan_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node: Planner.

    Input state keys consumed: issue, issue_id, repository
    Output state keys produced: plan, messages, latency_ms
    """
    start_ms = int(time.time() * 1000)
    logger.info(f"[Planner] Starting for issue {state['issue_id']}")

    try:
        plan = _call_llm_for_plan(
            issue=state["issue"],
            issue_id=state["issue_id"],
            repository=state["repository"],
        )
        elapsed = int(time.time() * 1000) - start_ms
        logger.info(f"[Planner] Completed in {elapsed}ms. Complexity: {plan.complexity}")

        return {
            "plan": plan,
            "status": "running",
            "messages": [{
                "node": "planner",
                "status": "success",
                "summary": plan.summary,
                "elapsed_ms": elapsed,
            }],
            "latency_ms": {**state.get("latency_ms", {}), "planner": elapsed},
        }

    except Exception as e:
        logger.error(f"[Planner] Failed: {e}")
        return {
            "error": f"Planner failed: {str(e)}",
            "status": "failed",
            "messages": [{"node": "planner", "status": "error", "error": str(e)}],
        }
