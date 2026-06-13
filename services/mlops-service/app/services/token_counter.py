"""
Token Counter & Cost Tracker — tracks LLM token usage and cost per query.

Supports:
  - Local Ollama: $0 per query (no API cost)
  - OpenAI GPT-4o-mini: ~$0.01 per 1K tokens
  - OpenAI GPT-4o: ~$0.05 per 1K tokens
  - Anthropic Claude 3.5 Sonnet: ~$0.015 per 1K tokens
  - Azure OpenAI: custom pricing per deployment

Alert: if cost > $0.10 per single query
Reporting: cost summary by time period, model, and endpoint
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

COST_ALERT_THRESHOLD = float(os.getenv("COST_ALERT_THRESHOLD_USD", "0.10"))

# Cost per 1M tokens (input / output)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input_per_1m": 5.00, "output_per_1m": 15.00},
    "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "gpt-3.5-turbo": {"input_per_1m": 0.50, "output_per_1m": 1.50},
    "claude-3-5-sonnet": {"input_per_1m": 3.00, "output_per_1m": 15.00},
    "claude-3-haiku": {"input_per_1m": 0.25, "output_per_1m": 1.25},
    # Local models: $0
    "llama3:8b": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "llama3:70b": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "mistral:7b": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "mock": {"input_per_1m": 0.0, "output_per_1m": 0.0},
}


@dataclass
class TokenUsageRecord:
    """A single token usage event."""
    record_id: str
    timestamp: str
    endpoint: str
    model: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: int
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    is_local: bool = False


class TokenCounter:
    """
    Per-query token usage and cost tracker.

    Usage:
        counter = TokenCounter()
        record = counter.record_usage(
            endpoint="/api/v1/rag",
            model="gpt-4o-mini",
            tokens_input=512,
            tokens_output=128,
            latency_ms=320,
        )
        summary = counter.get_summary(period_hours=24)
    """

    def __init__(self):
        self._records: List[TokenUsageRecord] = []
        self._total_cost = 0.0

    def compute_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """
        Compute USD cost for a given model and token counts.

        Args:
            model: Model identifier (e.g. "gpt-4o-mini", "llama3:8b").
            tokens_input: Number of input/prompt tokens.
            tokens_output: Number of output/completion tokens.

        Returns:
            Cost in USD.
        """
        # Normalize model name
        model_key = model.lower().split(":")[0]
        pricing = None
        for key in MODEL_PRICING:
            if key in model_key or model_key in key:
                pricing = MODEL_PRICING[key]
                break

        if pricing is None:
            # Unknown model: estimate at GPT-4o-mini pricing
            pricing = MODEL_PRICING["gpt-4o-mini"]
            logger.warning(f"[TokenCounter] Unknown model '{model}', using gpt-4o-mini pricing")

        input_cost = (tokens_input / 1_000_000) * pricing["input_per_1m"]
        output_cost = (tokens_output / 1_000_000) * pricing["output_per_1m"]
        return round(input_cost + output_cost, 6)

    def record_usage(
        self,
        endpoint: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: int = 0,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> TokenUsageRecord:
        """
        Record a single LLM usage event.

        Args:
            endpoint: API endpoint that made the LLM call.
            model: LLM model identifier.
            tokens_input: Input token count.
            tokens_output: Output token count.
            latency_ms: Response latency.
            user_id: Optional user identifier.
            session_id: Optional session identifier.

        Returns:
            TokenUsageRecord with computed cost.
        """
        cost = self.compute_cost(model, tokens_input, tokens_output)
        is_local = "llama" in model.lower() or "mistral" in model.lower() or model == "mock"

        record = TokenUsageRecord(
            record_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            endpoint=endpoint,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost,
            latency_ms=latency_ms,
            user_id=user_id,
            session_id=session_id,
            is_local=is_local,
        )

        self._records.append(record)
        self._total_cost += cost

        # Cost alert
        if cost > COST_ALERT_THRESHOLD:
            logger.warning(
                f"🚨 HIGH COST ALERT: ${cost:.4f} for single query "
                f"(threshold: ${COST_ALERT_THRESHOLD}) "
                f"model={model} endpoint={endpoint} "
                f"tokens={tokens_input}+{tokens_output}"
            )

        logger.info(
            f"[TokenCounter] {endpoint} | {model} | "
            f"in={tokens_input} out={tokens_output} | "
            f"cost=${cost:.4f} | latency={latency_ms}ms"
        )

        return record

    def get_summary(self, period_hours: int = 24) -> Dict[str, Any]:
        """
        Generate a cost summary for the given time period.

        Args:
            period_hours: Look-back period in hours.

        Returns:
            Summary dict with totals by model and endpoint.
        """
        cutoff = time.time() - (period_hours * 3600)
        recent = [
            r for r in self._records
            if self._parse_ts(r.timestamp) >= cutoff
        ]

        if not recent:
            return {
                "period_hours": period_hours,
                "total_cost_usd": 0.0,
                "total_queries": 0,
                "by_model": {},
                "by_endpoint": {},
                "local_vs_cloud": {"local_queries": 0, "cloud_queries": 0},
            }

        # Aggregate by model
        by_model: Dict[str, Dict] = {}
        by_endpoint: Dict[str, Dict] = {}
        local_count = 0
        cloud_count = 0

        for r in recent:
            # By model
            if r.model not in by_model:
                by_model[r.model] = {"queries": 0, "cost_usd": 0.0, "tokens_total": 0}
            by_model[r.model]["queries"] += 1
            by_model[r.model]["cost_usd"] += r.cost_usd
            by_model[r.model]["tokens_total"] += r.tokens_input + r.tokens_output

            # By endpoint
            if r.endpoint not in by_endpoint:
                by_endpoint[r.endpoint] = {"queries": 0, "cost_usd": 0.0}
            by_endpoint[r.endpoint]["queries"] += 1
            by_endpoint[r.endpoint]["cost_usd"] += r.cost_usd

            # Local vs cloud
            if r.is_local:
                local_count += 1
            else:
                cloud_count += 1

        total_cost = sum(r.cost_usd for r in recent)
        avg_cost = total_cost / len(recent) if recent else 0.0

        return {
            "period_hours": period_hours,
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_query_usd": round(avg_cost, 6),
            "total_queries": len(recent),
            "by_model": {k: {**v, "cost_usd": round(v["cost_usd"], 4)} for k, v in by_model.items()},
            "by_endpoint": {k: {**v, "cost_usd": round(v["cost_usd"], 4)} for k, v in by_endpoint.items()},
            "local_vs_cloud": {
                "local_queries": local_count,
                "cloud_queries": cloud_count,
                "local_savings_usd": round(
                    sum(r.cost_usd for r in recent if not r.is_local) * 0 +
                    local_count * 0.01, 4
                ),
            },
            "alert_threshold_usd": COST_ALERT_THRESHOLD,
        }

    def export_csv(self, path: str = "token_usage.csv"):
        """Export all records to CSV for analysis."""
        import csv
        fieldnames = [
            "record_id", "timestamp", "endpoint", "model",
            "tokens_input", "tokens_output", "cost_usd",
            "latency_ms", "user_id", "is_local"
        ]
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self._records:
                row = asdict(r)
                writer.writerow({k: row[k] for k in fieldnames})
        logger.info(f"[TokenCounter] Exported {len(self._records)} records to {path}")

    @staticmethod
    def _parse_ts(ts: str) -> float:
        """Parse ISO timestamp to Unix seconds."""
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0


# Singleton
token_counter = TokenCounter()
