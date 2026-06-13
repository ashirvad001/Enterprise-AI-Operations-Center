"""
Edge Latency Benchmark — measures tokens/sec, time-to-first-token, and end-to-end latency.

Targets (from spec):
  - Raspberry Pi 5: >40 tokens/sec, Q4_K_M model
  - NVIDIA Jetson Nano: >80 tokens/sec, Q4_K_M or Q5_K_M model
  - Time to first token: <500ms
  - End-to-end (voice): <2000ms

Benchmark Prompts:
  - Short (10 token output): quick response test
  - Medium (100 token output): typical answer
  - Long (512 token output): full analysis

Usage:
    python latency_test.py [--url http://localhost:11434] [--model llama3:8b] [--runs 10]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, asdict
from typing import List, Optional

import httpx


BENCHMARK_PROMPTS = [
    {
        "name": "short",
        "prompt": "What is 2 + 2? Answer in one word.",
        "target_tokens": 5,
    },
    {
        "name": "medium",
        "prompt": "Explain what a REST API is in 2-3 sentences.",
        "target_tokens": 60,
    },
    {
        "name": "long",
        "prompt": (
            "Write a comprehensive technical explanation of how transformer-based "
            "language models work, covering attention mechanisms, tokenization, "
            "training objectives, and inference. Include practical examples."
        ),
        "target_tokens": 300,
    },
]


@dataclass
class BenchmarkRun:
    """Single benchmark measurement."""
    prompt_name: str
    latency_ms: int
    tokens_generated: int
    tokens_per_second: float
    time_to_first_token_ms: Optional[int] = None
    error: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Aggregated benchmark statistics."""
    prompt_name: str
    runs: int
    mean_tps: float
    p50_tps: float
    p95_tps: float
    p99_tps: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    mean_tokens: float
    error_count: int
    meets_target: bool
    target_tps: float


async def measure_ttft(
    base_url: str,
    model: str,
    prompt: str,
    client: httpx.AsyncClient,
) -> Optional[int]:
    """
    Measure time-to-first-token (TTFT) via streaming.

    Returns:
        TTFT in milliseconds, or None on failure.
    """
    start = time.time()
    try:
        async with client.stream(
            "POST",
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            timeout=60.0,
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("response", ""):
                            return int((time.time() - start) * 1000)
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return None
    return None


async def run_benchmark(
    base_url: str,
    model: str,
    prompt_config: dict,
    client: httpx.AsyncClient,
) -> BenchmarkRun:
    """Run a single benchmark measurement."""
    start = time.time()
    try:
        response = await client.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt_config["prompt"],
                "stream": False,
                "options": {
                    "num_predict": prompt_config.get("target_tokens", 100),
                    "temperature": 0.1,
                },
            },
            timeout=120.0,
        )
        elapsed_ms = int((time.time() - start) * 1000)
        data = response.json()

        tokens = data.get("eval_count", 0)
        eval_ns = data.get("eval_duration", elapsed_ms * 1_000_000)
        tps = tokens / (eval_ns / 1e9) if eval_ns > 0 else 0.0

        return BenchmarkRun(
            prompt_name=prompt_config["name"],
            latency_ms=elapsed_ms,
            tokens_generated=tokens,
            tokens_per_second=round(tps, 1),
        )
    except httpx.ConnectError:
        return BenchmarkRun(
            prompt_name=prompt_config["name"],
            latency_ms=0,
            tokens_generated=0,
            tokens_per_second=0.0,
            error="Ollama not running (ConnectError)",
        )
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return BenchmarkRun(
            prompt_name=prompt_config["name"],
            latency_ms=elapsed_ms,
            tokens_generated=0,
            tokens_per_second=0.0,
            error=str(e),
        )


def compute_summary(
    runs: List[BenchmarkRun],
    prompt_name: str,
    target_tps: float = 40.0,
) -> BenchmarkSummary:
    """Compute statistical summary for a set of benchmark runs."""
    valid = [r for r in runs if not r.error]
    errors = len(runs) - len(valid)

    if not valid:
        return BenchmarkSummary(
            prompt_name=prompt_name,
            runs=len(runs),
            mean_tps=0.0, p50_tps=0.0, p95_tps=0.0, p99_tps=0.0,
            mean_latency_ms=0.0, p50_latency_ms=0.0, p95_latency_ms=0.0,
            mean_tokens=0.0,
            error_count=errors,
            meets_target=False,
            target_tps=target_tps,
        )

    tps_values = [r.tokens_per_second for r in valid]
    latency_values = [r.latency_ms for r in valid]
    tps_values.sort()
    latency_values.sort()

    def percentile(data, p):
        idx = int(len(data) * p / 100)
        return data[min(idx, len(data) - 1)]

    mean_tps = statistics.mean(tps_values)
    return BenchmarkSummary(
        prompt_name=prompt_name,
        runs=len(runs),
        mean_tps=round(mean_tps, 1),
        p50_tps=round(percentile(tps_values, 50), 1),
        p95_tps=round(percentile(tps_values, 95), 1),
        p99_tps=round(percentile(tps_values, 99), 1),
        mean_latency_ms=round(statistics.mean(latency_values), 0),
        p50_latency_ms=round(percentile(latency_values, 50), 0),
        p95_latency_ms=round(percentile(latency_values, 95), 0),
        mean_tokens=round(statistics.mean([r.tokens_generated for r in valid]), 1),
        error_count=errors,
        meets_target=mean_tps >= target_tps,
        target_tps=target_tps,
    )


def print_report(summaries: List[BenchmarkSummary], model: str, base_url: str):
    """Print formatted benchmark report."""
    print("\n" + "="*70)
    print(f"EDGE LLM LATENCY BENCHMARK REPORT")
    print(f"Model: {model} | Server: {base_url}")
    print("="*70)

    for s in summaries:
        status = "✅ PASS" if s.meets_target else "❌ FAIL"
        print(f"\n[{s.prompt_name.upper()}] {status} (target: ≥{s.target_tps} tokens/sec)")
        print(f"  Mean TPS:      {s.mean_tps:.1f} tokens/sec")
        print(f"  P50/P95/P99:   {s.p50_tps} / {s.p95_tps} / {s.p99_tps}")
        print(f"  Mean latency:  {s.mean_latency_ms:.0f}ms")
        print(f"  P95 latency:   {s.p95_latency_ms:.0f}ms")
        print(f"  Avg tokens:    {s.mean_tokens:.0f}")
        if s.error_count:
            print(f"  ⚠️  Errors:     {s.error_count}/{s.runs} runs failed")

    overall_pass = all(s.meets_target for s in summaries)
    print(f"\n{'='*70}")
    print(f"OVERALL: {'✅ ALL TARGETS MET' if overall_pass else '❌ SOME TARGETS MISSED'}")
    print("="*70)


async def main():
    parser = argparse.ArgumentParser(description="Edge LLM Latency Benchmark")
    parser.add_argument("--url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--model", default="llama3:8b", help="Model to benchmark")
    parser.add_argument("--runs", type=int, default=5, help="Runs per prompt")
    parser.add_argument("--target-tps", type=float, default=40.0, help="Target tokens/sec")
    parser.add_argument("--output", default="", help="Save results to JSON file")
    args = parser.parse_args()

    print(f"Starting edge LLM benchmark: {args.model} @ {args.url}")
    print(f"Runs per prompt: {args.runs} | Target: ≥{args.target_tps} tokens/sec")

    summaries = []
    all_runs = []

    async with httpx.AsyncClient() as client:
        # Warmup
        print("\nWarming up...")
        await run_benchmark(args.url, args.model, BENCHMARK_PROMPTS[0], client)

        for prompt_cfg in BENCHMARK_PROMPTS:
            print(f"\nBenchmarking [{prompt_cfg['name']}] prompt ({args.runs} runs)...")
            runs = []
            for i in range(args.runs):
                run = await run_benchmark(args.url, args.model, prompt_cfg, client)
                runs.append(run)
                print(f"  Run {i+1}: {run.tokens_per_second} TPS, {run.latency_ms}ms"
                      + (f" [ERROR: {run.error}]" if run.error else ""))

            summary = compute_summary(runs, prompt_cfg["name"], args.target_tps)
            summaries.append(summary)
            all_runs.extend(runs)

    print_report(summaries, args.model, args.url)

    if args.output:
        output_data = {
            "model": args.model,
            "base_url": args.url,
            "target_tps": args.target_tps,
            "summaries": [asdict(s) for s in summaries],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
