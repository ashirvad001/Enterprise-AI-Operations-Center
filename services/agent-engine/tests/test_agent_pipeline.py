"""
Phase 1 Agent Pipeline Tests — 10 GitHub issues with known bugs.

Tests cover:
  - Planner: produces structured IssuePlan with required fields
  - Coder: produces valid Python code
  - SecurityReviewer: detects hardcoded secrets, SQL injection, eval usage
  - Tester: generates pytest test files with correct structure
  - Orchestrator: full pipeline runs end-to-end without error

Metrics tracked:
  - Plan quality (all required fields present)
  - Security detection rate (known issues flagged)
  - False positive rate (clean code flagged as unsafe)
  - Test coverage targets (functions listed in test suite)
  - End-to-end latency per pipeline run
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.agents.planner import plan_node
from app.agents.coder import code_node
from app.agents.security_reviewer import security_review_node, _analyze_code_static
from app.agents.tester import tester_node
from app.agents.state import AgentState, IssuePlan, CodeOutput, SecurityAnalysis


# ---------------------------------------------------------------------------
# Test Dataset: 10 GitHub Issues With Known Bugs
# ---------------------------------------------------------------------------

GITHUB_ISSUES = [
    {
        "issue_id": "GH-001",
        "title": "SQL injection in user search endpoint",
        "issue": """
Bug: The user search endpoint is vulnerable to SQL injection.
The query is built using string formatting:
  query = f"SELECT * FROM users WHERE name = '{user_input}'"
This allows attackers to inject arbitrary SQL.
Repository: org/backend-api
Expected fix: Use parameterized queries.
""",
        "expected_security_issue": "sql_injection",
        "repository": "org/backend-api",
    },
    {
        "issue_id": "GH-002",
        "title": "Hardcoded AWS credentials in config.py",
        "issue": """
Bug: AWS credentials are hardcoded in config.py:
  AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
These should be loaded from environment variables.
""",
        "expected_security_issue": "hardcoded_secret",
        "repository": "org/infra-config",
    },
    {
        "issue_id": "GH-003",
        "title": "Use of eval() on user-provided input causes RCE",
        "issue": """
Critical: The following code evaluates user input directly:
  result = eval(request.data.get("expression"))
This allows remote code execution. Replace with a safe expression parser.
""",
        "expected_security_issue": "dangerous_call",
        "repository": "org/calculator-api",
    },
    {
        "issue_id": "GH-004",
        "title": "KeyError crash when user profile is incomplete",
        "issue": """
Bug: The profile endpoint crashes with KeyError when a user has no 'email' field.
  email = user_data['email']  # crashes for new users
Fix: Use .get() with a default value.
""",
        "expected_security_issue": None,
        "repository": "org/user-service",
    },
    {
        "issue_id": "GH-005",
        "title": "Off-by-one error in pagination logic",
        "issue": """
Bug: Pagination returns one extra item on the last page.
  items = results[page * page_size : (page + 1) * page_size]
When page=last_page, this overflows and includes a duplicate item.
Fix: Add bounds check before slicing.
""",
        "expected_security_issue": None,
        "repository": "org/api-gateway",
    },
    {
        "issue_id": "GH-006",
        "title": "Race condition in cache invalidation",
        "issue": """
Bug: Cache invalidation has a race condition under concurrent writes.
Two threads can simultaneously read stale cache, both update DB, and 
the second write overwrites the first. Use Redis SETNX or a lock.
""",
        "expected_security_issue": None,
        "repository": "org/cache-service",
    },
    {
        "issue_id": "GH-007",
        "title": "Missing input validation on file upload endpoint",
        "issue": """
Bug: The file upload endpoint does not validate file type or size.
Users can upload files of any type (including .exe, .sh) without restriction.
Add MIME type validation and a 10MB size limit.
""",
        "expected_security_issue": None,
        "repository": "org/file-service",
    },
    {
        "issue_id": "GH-008",
        "title": "Unhandled exception causes 500 error on empty search",
        "issue": """
Bug: Searching with an empty string causes an unhandled AttributeError:
  results = query.filter(Model.name.contains(search_term))
  # crashes when search_term is None
Fix: Add None check before calling .contains().
""",
        "expected_security_issue": None,
        "repository": "org/search-service",
    },
    {
        "issue_id": "GH-009",
        "title": "Memory leak in WebSocket connection handler",
        "issue": """
Bug: WebSocket connections are not properly closed when clients disconnect.
The connection object is stored in a global dict but never removed, causing
memory to grow unbounded. Add disconnect handler to clean up.
""",
        "expected_security_issue": None,
        "repository": "org/realtime-service",
    },
    {
        "issue_id": "GH-010",
        "title": "Incorrect HTTP status code for validation errors",
        "issue": """
Bug: When request validation fails, the API returns 500 instead of 422.
The pydantic ValidationError is not caught and re-raised as an HTTPException.
Fix: Wrap validation logic in try/except and return 422 with error details.
""",
        "expected_security_issue": None,
        "repository": "org/api-service",
    },
]

# Code samples for security testing
CLEAN_CODE = '''
def get_user(user_id: int) -> dict:
    """Retrieves a user safely using parameterized queries."""
    user = db.session.query(User).filter(User.id == user_id).first()
    if not user:
        return {}
    return {"id": user.id, "name": user.name, "email": user.email}
'''

SQL_INJECTION_CODE = '''
def search_users(name: str) -> list:
    """UNSAFE: Uses string formatting in SQL query."""
    query = f"SELECT * FROM users WHERE name = '{name}'"
    return db.execute(query).fetchall()
'''

HARDCODED_SECRET_CODE = '''
import requests

API_KEY = "sk-proj-abc123secretkey"
PASSWORD = "admin_password_123"

def call_api():
    return requests.get("https://api.example.com", headers={"Authorization": API_KEY})
'''

EVAL_CODE = '''
def calculate(expression: str) -> float:
    """UNSAFE: Evaluates user-provided expression."""
    return eval(expression)
'''


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _make_base_state(issue_data: Dict[str, Any]) -> AgentState:
    """Creates a base AgentState from an issue dict."""
    return AgentState(
        run_id="test-run",
        issue=issue_data["issue"],
        issue_id=issue_data["issue_id"],
        repository=issue_data.get("repository", "org/repo"),
        plan=None,
        code=None,
        security_review=None,
        tests=None,
        pr=None,
        iteration=0,
        max_iterations=3,
        human_approved=False,
        error=None,
        status="running",
        messages=[],
        total_tokens_used=0,
        total_cost_usd=0.0,
        latency_ms={},
    )


# ---------------------------------------------------------------------------
# Phase 1 Tests
# ---------------------------------------------------------------------------

class TestPlannerNode:
    """Tests for the Planner agent node."""

    @pytest.mark.parametrize("issue_data", GITHUB_ISSUES, ids=[i["issue_id"] for i in GITHUB_ISSUES])
    def test_planner_produces_valid_plan(self, issue_data):
        """Planner should return a valid IssuePlan for any GitHub issue."""
        state = _make_base_state(issue_data)
        result = plan_node(state)

        assert "plan" in result, "plan_node must return 'plan' key"
        plan = result["plan"]
        assert plan is not None, "Plan should not be None"
        assert plan.issue_id, "Plan must have issue_id"
        assert plan.summary, "Plan must have summary"
        assert plan.root_cause, "Plan must have root_cause"
        assert isinstance(plan.steps, list), "Steps must be a list"
        assert len(plan.steps) >= 1, "Plan must have at least 1 step"
        assert plan.complexity in {"low", "medium", "high"}, f"Invalid complexity: {plan.complexity}"

    def test_planner_status_running_on_success(self):
        """Planner should set status='running' on success."""
        state = _make_base_state(GITHUB_ISSUES[0])
        result = plan_node(state)
        assert result.get("status") == "running"

    def test_planner_adds_message(self):
        """Planner should add a message to the messages list."""
        state = _make_base_state(GITHUB_ISSUES[0])
        result = plan_node(state)
        assert len(result.get("messages", [])) == 1
        assert result["messages"][0]["node"] == "planner"

    def test_planner_records_latency(self):
        """Planner should record latency_ms for the planner node."""
        state = _make_base_state(GITHUB_ISSUES[0])
        result = plan_node(state)
        assert "latency_ms" in result
        assert "planner" in result["latency_ms"]
        assert result["latency_ms"]["planner"] >= 0


class TestCoderNode:
    """Tests for the Coder agent node."""

    def _state_with_plan(self, issue_data: Dict) -> AgentState:
        state = _make_base_state(issue_data)
        plan_result = plan_node(state)
        state.update(plan_result)
        state["messages"] = plan_result.get("messages", [])
        return state

    @pytest.mark.parametrize("issue_data", GITHUB_ISSUES[:5], ids=[i["issue_id"] for i in GITHUB_ISSUES[:5]])
    def test_coder_produces_valid_code(self, issue_data):
        """Coder should produce a CodeOutput with non-empty code."""
        state = self._state_with_plan(issue_data)
        result = code_node(state)

        assert "code" in result, "code_node must return 'code' key"
        code = result["code"]
        assert code is not None
        assert code.filename, "CodeOutput must have a filename"
        assert code.code, "CodeOutput must have code"
        assert code.language, "CodeOutput must have language"
        assert len(code.code) > 20, "Code should not be trivially short"

    def test_coder_fails_gracefully_without_plan(self):
        """Coder should set status=failed if no plan is available."""
        state = _make_base_state(GITHUB_ISSUES[0])
        # Don't add a plan
        result = code_node(state)
        assert result.get("status") == "failed"
        assert result.get("error") is not None


class TestSecurityReviewerNode:
    """Tests for the SecurityReviewer agent node."""

    def _make_state_with_code(self, code_str: str, filename: str = "fix.py") -> AgentState:
        state = _make_base_state(GITHUB_ISSUES[0])
        state["plan"] = IssuePlan(
            issue_id="GH-001",
            summary="Test issue",
            root_cause="Unknown",
            affected_files=[filename],
            steps=["Fix it"],
            complexity="low",
        )
        state["code"] = CodeOutput(
            filename=filename,
            language="python",
            code=code_str,
            diff_summary="Test code",
            dependencies=[],
        )
        return state

    def test_clean_code_passes_review(self):
        """Clean code should pass security review."""
        state = self._make_state_with_code(CLEAN_CODE)
        result = security_review_node(state)
        review = result["security_review"]
        assert review.passed is True, f"Expected pass but got: {review.vulnerabilities}"

    def test_sql_injection_is_detected(self):
        """SQL injection patterns should be flagged."""
        analysis = _analyze_code_static(SQL_INJECTION_CODE)
        sql_types = [v["type"] for v in analysis.vulnerabilities]
        assert "sql_injection" in sql_types, f"SQL injection not detected. Found: {sql_types}"
        assert not analysis.passed

    def test_hardcoded_secret_is_detected(self):
        """Hardcoded API keys/passwords should be flagged as CRITICAL."""
        analysis = _analyze_code_static(HARDCODED_SECRET_CODE)
        secret_types = [v["type"] for v in analysis.vulnerabilities]
        assert "hardcoded_secret" in secret_types, f"Hardcoded secret not detected. Found: {secret_types}"
        critical = [v for v in analysis.vulnerabilities if v["severity"] == "CRITICAL"]
        assert len(critical) > 0

    def test_eval_usage_is_detected(self):
        """eval() calls should be flagged as HIGH or CRITICAL."""
        analysis = _analyze_code_static(EVAL_CODE)
        dangerous = [v for v in analysis.vulnerabilities if v["type"] == "dangerous_call"]
        assert len(dangerous) > 0, "eval() usage not detected"
        severities = {v["severity"] for v in dangerous}
        assert severities & {"HIGH", "CRITICAL"}, f"Wrong severity: {severities}"

    def test_security_review_fails_without_code(self):
        """Security reviewer should fail gracefully without code."""
        state = _make_base_state(GITHUB_ISSUES[0])
        result = security_review_node(state)
        assert result.get("status") == "failed"

    def test_security_detection_rate(self):
        """At least 3 out of 4 test vulnerabilities must be detected."""
        vulnerable_codes = [
            (SQL_INJECTION_CODE, "sql_injection"),
            (HARDCODED_SECRET_CODE, "hardcoded_secret"),
            (EVAL_CODE, "dangerous_call"),
        ]
        detected = 0
        for code, expected_type in vulnerable_codes:
            analysis = _analyze_code_static(code)
            found_types = [v["type"] for v in analysis.vulnerabilities]
            if expected_type in found_types:
                detected += 1

        detection_rate = detected / len(vulnerable_codes)
        assert detection_rate >= 0.80, (
            f"Security detection rate {detection_rate:.0%} is below 80% target"
        )

    def test_false_positive_rate(self):
        """Clean code should not generate false positives."""
        analysis = _analyze_code_static(CLEAN_CODE)
        # Clean code should pass
        assert analysis.passed, f"False positive: clean code flagged. Vulns: {analysis.vulnerabilities}"


class TestTesterNode:
    """Tests for the Tester agent node."""

    def _full_pipeline_state(self, issue_data: Dict) -> AgentState:
        state = _make_base_state(issue_data)

        result = plan_node(state)
        state.update(result)

        result = code_node(state)
        state.update(result)

        result = security_review_node(state)
        state.update(result)

        return state

    def test_tester_produces_test_file(self):
        """Tester should produce a TestSuite with a valid Python test file."""
        state = self._full_pipeline_state(GITHUB_ISSUES[3])  # GH-004: clean issue
        result = tester_node(state)

        assert "tests" in result
        tests = result["tests"]
        assert tests.filename.endswith(".py"), "Test file must be .py"
        assert tests.test_count > 0, "At least 1 test should be generated"
        assert "def test_" in tests.test_code, "Test file must contain test functions"
        assert "pytest" in tests.test_code or "import" in tests.test_code

    def test_tester_covers_happy_path_and_edge_cases(self):
        """Generated tests should cover both happy path and edge cases."""
        state = self._full_pipeline_state(GITHUB_ISSUES[3])
        result = tester_node(state)
        tests = result["tests"]

        # Check for edge case coverage
        has_edge_case = (
            "None" in tests.test_code or
            "empty" in tests.test_code.lower() or
            "edge" in tests.test_code.lower() or
            "invalid" in tests.test_code.lower()
        )
        assert has_edge_case, "Tests should cover edge cases"

    def test_tester_status_awaiting_human(self):
        """After tester, status should be 'awaiting_human' (next: human checkpoint)."""
        state = self._full_pipeline_state(GITHUB_ISSUES[4])
        result = tester_node(state)
        assert result.get("status") == "awaiting_human"


class TestFullPipeline:
    """End-to-end pipeline tests."""

    @pytest.mark.asyncio
    async def test_full_pipeline_completes(self):
        """Full pipeline (planner → coder → reviewer → tester) should complete without error."""
        from app.engine import AgentEngine
        eng = AgentEngine()

        start = time.time()
        result = await eng.execute(
            issue=GITHUB_ISSUES[3]["issue"],
            issue_id=GITHUB_ISSUES[3]["issue_id"],
            repository=GITHUB_ISSUES[3]["repository"],
        )
        elapsed = time.time() - start

        assert result.get("status") in {"completed", "awaiting_human"}, (
            f"Expected completed/awaiting_human, got: {result.get('status')}"
        )
        assert result.get("plan") is not None, "Plan should be present"
        assert result.get("code") is not None, "Code should be present"
        assert result.get("security_review") is not None, "Security review should be present"
        assert result.get("tests") is not None, "Tests should be present"

        # Log pipeline metrics
        print(f"\n[Pipeline E2E] Total time: {elapsed:.2f}s")
        print(f"[Pipeline E2E] Status: {result.get('status')}")
        print(f"[Pipeline E2E] Latency breakdown: {result.get('latency_ms')}")

    def test_pipeline_handles_empty_issue(self):
        """Pipeline should handle empty issue gracefully."""
        from app.engine import engine
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            engine.execute(issue="", issue_id="GH-EMPTY", repository="org/test")
        )
        # Should not crash — either complete with mock output or fail gracefully
        assert result.get("status") in {"completed", "awaiting_human", "failed"}


# ---------------------------------------------------------------------------
# Metrics Summary (runs after all tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def print_metrics_summary(request):
    """Print aggregate metrics after all tests complete."""
    yield
    print("\n" + "="*60)
    print("PHASE 1 AGENT PIPELINE — TEST METRICS SUMMARY")
    print("="*60)
    print(f"  Total issues tested:     {len(GITHUB_ISSUES)}")
    print(f"  Security patterns:       SQL injection, hardcoded secrets, eval/exec")
    print(f"  Detection rate target:   >80%")
    print(f"  False positive target:   <10%")
    print("="*60)
