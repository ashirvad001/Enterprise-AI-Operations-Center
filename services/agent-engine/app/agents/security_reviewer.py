"""
Security Reviewer Agent Node — Phase 3 of the multi-agent pipeline.

Responsibilities:
  - Static analysis of the generated code using Python AST
  - Detect: hardcoded secrets, SQL injection risk, eval/exec usage,
    shell injection, unsafe deserialization, path traversal, XSS patterns
  - Return a SecurityAnalysis with severity-tagged vulnerabilities

Uses AST parsing (no LLM required for static checks) + optional LLM deep analysis.
"""

from __future__ import annotations

import ast
import logging
import re
import time
from typing import Any, Dict, List

from .state import AgentState, CodeOutput, SecurityAnalysis

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static Analysis Rules
# ---------------------------------------------------------------------------

# Patterns that suggest hardcoded secrets
SECRET_PATTERNS = [
    r'(?i)(password|passwd|secret|api_key|apikey|token|auth_key)\s*=\s*["\'][^"\']{4,}["\']',
    r'(?i)(aws_secret|aws_access_key|private_key)\s*=\s*["\'][^"\']{4,}["\']',
]

# SQL injection risk: string formatting into SQL queries
SQL_INJECTION_PATTERNS = [
    r'(?i)(execute|executemany|raw|query)\s*\(\s*f["\'].*?\{',
    r'(?i)(execute|executemany|raw|query)\s*\(\s*["\'].*?%\s*\(',
    r'(?i)(cursor\.|db\.|session\.|conn\.)?execute\s*\(\s*["\'][^"\']*\+',
    r'(?i)(execute|executemany|raw|query)\s*\(\s*f["\'].*?\{',
    r'(?i)execute\s*\(\s*["\'].*?\{.*?\}.*?["\']\s*\)',
    r'(?i)execute\s*\(\s*query\s*\)'
]

# Dangerous Python builtins
DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__", "subprocess.call",
                   "subprocess.Popen", "os.system", "pickle.loads", "yaml.load"}

# XSS patterns (for web-layer code)
XSS_PATTERNS = [
    r'(?i)mark_safe\s*\(',
    r'(?i)innerHTML\s*=',
    r'(?i)document\.write\s*\(',
]

# Path traversal
PATH_TRAVERSAL_PATTERNS = [
    r'(?i)open\s*\(\s*.*\+',
    r'(?i)os\.path\.join\s*\(\s*.*request',
]


class ASTSecurityVisitor(ast.NodeVisitor):
    """Walks the AST tree and collects security findings."""

    def __init__(self):
        self.findings: List[Dict[str, Any]] = []
        self.dangerous_calls_found: List[str] = []

    def visit_Call(self, node: ast.Call):
        # Check for dangerous function calls
        call_name = ""
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                call_name = f"{node.func.value.id}.{node.func.attr}"

        if call_name in DANGEROUS_CALLS:
            self.findings.append({
                "type": "dangerous_call",
                "severity": "HIGH" if call_name in {"eval", "exec", "pickle.loads"} else "MEDIUM",
                "line": node.lineno,
                "description": f"Dangerous call detected: {call_name}(). Consider safer alternatives.",
            })
            self.dangerous_calls_found.append(call_name)

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        dangerous_modules = {"pickle", "marshal", "shelve"}
        for alias in node.names:
            if alias.name in dangerous_modules:
                self.findings.append({
                    "type": "dangerous_import",
                    "severity": "MEDIUM",
                    "line": node.lineno,
                    "description": f"Import of potentially unsafe module: {alias.name}",
                })
        self.generic_visit(node)


def _check_patterns(code: str, patterns: List[str], finding_type: str, severity: str) -> List[str]:
    """Run regex patterns against code and return matched lines."""
    matches = []
    for line_num, line in enumerate(code.splitlines(), 1):
        for pattern in patterns:
            if re.search(pattern, line):
                matches.append(f"Line {line_num}: {line.strip()[:120]}")
    return matches


def _analyze_code_static(code: str) -> SecurityAnalysis:
    """
    Performs full static security analysis on a Python code string.
    Combines AST analysis + regex pattern matching.
    """
    findings: List[Dict[str, Any]] = []
    hardcoded_secrets: List[str] = []
    sql_risks: List[str] = []
    recommendations: List[str] = []

    # --- 1. AST Analysis ---
    ast_findings = []
    try:
        tree = ast.parse(code)
        visitor = ASTSecurityVisitor()
        visitor.visit(tree)
        ast_findings = visitor.findings
        findings.extend(ast_findings)
        if visitor.dangerous_calls_found:
            recommendations.append(
                f"Replace dangerous calls ({', '.join(visitor.dangerous_calls_found)}) "
                "with safer alternatives."
            )
    except SyntaxError as e:
        findings.append({
            "type": "syntax_error",
            "severity": "CRITICAL",
            "line": e.lineno,
            "description": f"Syntax error in generated code: {e.msg}",
        })

    # --- 2. Hardcoded Secrets ---
    secret_matches = _check_patterns(code, SECRET_PATTERNS, "hardcoded_secret", "CRITICAL")
    if secret_matches:
        hardcoded_secrets.extend(secret_matches)
        for m in secret_matches:
            findings.append({
                "type": "hardcoded_secret",
                "severity": "CRITICAL",
                "line": m.split(":")[0].replace("Line ", ""),
                "description": f"Potential hardcoded credential: {m}",
            })
        recommendations.append("Move all secrets to environment variables or a secrets manager (e.g. AWS Secrets Manager).")

    # --- 3. SQL Injection ---
    sql_matches = _check_patterns(code, SQL_INJECTION_PATTERNS, "sql_injection", "HIGH")
    if sql_matches:
        sql_risks.extend(sql_matches)
        for m in sql_matches:
            findings.append({
                "type": "sql_injection",
                "severity": "HIGH",
                "line": m.split(":")[0].replace("Line ", ""),
                "description": f"Possible SQL injection via string formatting: {m}",
            })
        recommendations.append("Use parameterized queries or ORM (SQLAlchemy) instead of string-format SQL.")

    # --- 4. XSS ---
    xss_matches = _check_patterns(code, XSS_PATTERNS, "xss", "HIGH")
    for m in xss_matches:
        findings.append({
            "type": "xss",
            "severity": "HIGH",
            "line": m.split(":")[0].replace("Line ", ""),
            "description": f"Possible XSS vulnerability: {m}",
        })
    if xss_matches:
        recommendations.append("Escape all user-controlled output before rendering in HTML.")

    # --- 5. Path Traversal ---
    path_matches = _check_patterns(code, PATH_TRAVERSAL_PATTERNS, "path_traversal", "HIGH")
    for m in path_matches:
        findings.append({
            "type": "path_traversal",
            "severity": "HIGH",
            "line": m.split(":")[0].replace("Line ", ""),
            "description": f"Possible path traversal: {m}",
        })
    if path_matches:
        recommendations.append("Validate and sanitize all file paths. Use os.path.abspath() and restrict to allowed directories.")

    # Determine pass/fail
    critical_or_high = [f for f in findings if f.get("severity") in {"CRITICAL", "HIGH"}]
    passed = len(critical_or_high) == 0

    if not recommendations and passed:
        recommendations.append("No critical security issues found. Code passed static security review.")

    return SecurityAnalysis(
        passed=passed,
        vulnerabilities=findings,
        hardcoded_secrets=hardcoded_secrets,
        sql_injection_risks=sql_risks,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# LangGraph Node Function
# ---------------------------------------------------------------------------

def security_review_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node: Security Reviewer.

    Input state keys consumed: code
    Output state keys produced: security_review, messages, latency_ms
    """
    start_ms = int(time.time() * 1000)

    if not state.get("code"):
        return {
            "error": "Security Reviewer received no code from Coder",
            "status": "failed",
            "messages": [{"node": "security_reviewer", "status": "error", "error": "Missing code"}],
        }

    code_output: CodeOutput = state["code"]
    logger.info(f"[SecurityReviewer] Analyzing {code_output.filename}")

    try:
        analysis = _analyze_code_static(code_output.code)
        elapsed = int(time.time() * 1000) - start_ms

        vuln_count = len(analysis.vulnerabilities)
        critical = [v for v in analysis.vulnerabilities if v.get("severity") == "CRITICAL"]
        logger.info(
            f"[SecurityReviewer] Done in {elapsed}ms. "
            f"Passed={analysis.passed}, Vulns={vuln_count}, Critical={len(critical)}"
        )

        return {
            "security_review": analysis,
            "status": "running",
            "messages": [{
                "node": "security_reviewer",
                "status": "success",
                "passed": analysis.passed,
                "vulnerability_count": vuln_count,
                "critical_count": len(critical),
                "elapsed_ms": elapsed,
            }],
            "latency_ms": {**state.get("latency_ms", {}), "security_reviewer": elapsed},
        }

    except Exception as e:
        logger.error(f"[SecurityReviewer] Failed: {e}")
        return {
            "error": f"Security reviewer failed: {str(e)}",
            "status": "failed",
            "messages": [{"node": "security_reviewer", "status": "error", "error": str(e)}],
        }
