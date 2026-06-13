"""
Shared LangGraph state definition for the multi-agent code review pipeline.

All agent nodes read from and write to this single TypedDict state object,
which LangGraph persists across the execution graph.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field
import operator


# ---------------------------------------------------------------------------
# Pydantic structured output schemas (used by LLM function-calling)
# ---------------------------------------------------------------------------

class IssuePlan(BaseModel):
    """Structured plan produced by the Planner agent."""
    issue_id: str = Field(description="The GitHub issue number or identifier")
    summary: str = Field(description="One-sentence summary of the issue")
    root_cause: str = Field(description="Suspected root cause of the bug/feature")
    affected_files: List[str] = Field(description="List of files likely needing changes")
    steps: List[str] = Field(description="Ordered steps to resolve the issue")
    complexity: str = Field(description="low | medium | high")


class CodeOutput(BaseModel):
    """Structured code fix produced by the Coder agent."""
    filename: str = Field(description="The primary file being changed")
    language: str = Field(description="Programming language, e.g. python")
    code: str = Field(description="The complete fixed code block")
    diff_summary: str = Field(description="Human-readable summary of changes made")
    dependencies: List[str] = Field(default_factory=list, description="Any new pip packages required")


class SecurityAnalysis(BaseModel):
    """Security review result from the SecurityReviewer agent."""
    passed: bool = Field(description="True if no critical issues found")
    vulnerabilities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of {type, severity, line, description} dicts"
    )
    hardcoded_secrets: List[str] = Field(
        default_factory=list,
        description="List of variable names/patterns that appear to be hardcoded secrets"
    )
    sql_injection_risks: List[str] = Field(
        default_factory=list,
        description="Lines or patterns with SQL injection risk"
    )
    recommendations: List[str] = Field(default_factory=list)


class TestSuite(BaseModel):
    """Generated pytest test suite from the Tester agent."""
    filename: str = Field(description="Test file name, e.g. test_fix.py")
    test_code: str = Field(description="Complete pytest test file content")
    test_count: int = Field(description="Number of test functions generated")
    coverage_target: List[str] = Field(
        default_factory=list,
        description="Functions/methods targeted by the tests"
    )


class PROutput(BaseModel):
    """Final PR metadata for GitHub."""
    title: str
    body: str
    branch_name: str
    base_branch: str = "main"
    labels: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# LangGraph TypedDict State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """
    The shared state object that flows through all nodes in the LangGraph.

    Each agent node receives the full state, performs its task,
    and returns a partial dict of keys to update.
    """
    # Input
    run_id: str
    issue: str                          # Raw GitHub issue description/body
    issue_id: str                       # e.g. "GH-142"
    repository: str                     # e.g. "org/repo"

    # Agent outputs (accumulated through graph)
    plan: Optional[IssuePlan]
    code: Optional[CodeOutput]
    security_review: Optional[SecurityAnalysis]
    tests: Optional[TestSuite]
    pr: Optional[PROutput]

    # Control flow
    iteration: int                      # Retry counter
    max_iterations: int                 # Max retries (default 3)
    human_approved: bool                # Set True at human checkpoint
    error: Optional[str]               # Last error message if any
    status: str                        # "running" | "awaiting_human" | "completed" | "failed"

    # Accumulated messages for audit trail
    messages: Annotated[List[Dict[str, Any]], operator.add]

    # Metrics
    total_tokens_used: int
    total_cost_usd: float
    latency_ms: Dict[str, int]         # per-node latency tracking
