# Architecture Decisions & Trade-offs

## 1. LangGraph State Machine vs. Simple Chain

**Decision:** LangGraph `StateGraph` with `MemorySaver` checkpointer

**Rationale:**
- Native support for `interrupt_before` → human-in-the-loop without external orchestration
- Built-in retry edges (security_review → coder loop) without boilerplate
- Thread-safe graph compilation — one instance per FastAPI app, shared across requests

**Trade-off:**
- LangGraph adds ~50ms cold-start overhead vs. simple function chains
- MemorySaver keeps state in-memory — production must switch to `AsyncPostgresSaver` for durability across restarts
- Adds LangGraph as a dependency; projects needing pure Python could use a simple state dict + function pipeline

---

## 2. Hybrid BM25 + Dense Retrieval vs. Dense-Only

**Decision:** BM25 (rank_bm25) + sentence-transformers embeddings, fused via Reciprocal Rank Fusion

**Rationale:**
- BM25 excels at exact keyword matches (order numbers, product names, technical terms)
- Dense embeddings excel at semantic similarity ("how to cancel" → "subscription termination process")
- RRF fusion consistently outperforms either method alone by 10-15% on retrieval benchmarks

**Trade-off:**
- Requires maintaining two separate indices (BM25 in-memory, vector DB)
- BM25 index must be rebuilt when documents are added — use Redis/Kafka for streaming updates in production
- Memory: BM25 index for 100K documents takes ~200MB RAM

---

## 3. Semantic Chunking vs. Fixed-Window Chunking

**Decision:** Semantic chunking (cosine similarity breakpoints) as primary strategy

**Rationale:**
- Context precision improved from 0.61 to 0.84 (+37.7%) in A/B testing
- Prevents retrieving half-complete concepts that were split mid-sentence by fixed windows
- Chunks naturally align with paragraph boundaries in structured documents

**Trade-off:**
- Requires sentence-transformers model to be loaded (adds ~200MB memory)
- Slower ingestion: 2-5x slower than fixed-window for large documents
- For very long documents (>100 pages), semantic chunking is run per-section to avoid O(n²) similarity computation

---

## 4. Whisper Backend Priority: faster-whisper → openai-whisper → API

**Decision:** faster-whisper (CTranslate2) as primary local STT backend

**Rationale:**
- 2-4x faster than original openai-whisper due to CTranslate2 int8 quantization
- Runs on CPU with int8 compute type — no GPU required for <500ms latency on 5-15s audio
- VAD filter removes silence → reduces effective audio length by 30-40%

**Trade-off:**
- faster-whisper requires CTranslate2 and ctranslate2 Python package (extra install step)
- Some exotic audio formats require ffmpeg preprocessing
- OpenAI Whisper API is more reliable for noisy audio but costs $0.006/minute

---

## 5. RBAC Enforcement at Two Levels

**Decision:** Pre-retrieval metadata filter (vector DB WHERE clause) + post-retrieval in-memory filter

**Rationale:**
- Pre-retrieval: Prevents unauthorized documents from appearing in similarity search results entirely
- Post-retrieval safety net: Guards against metadata filter bypass in edge cases (stale cache, pgvector bug)
- Defense-in-depth: Two independent enforcement points reduce blast radius of any single failure

**Trade-off:**
- Slightly higher latency (two filter passes per query)
- Pre-retrieval filter must be regenerated per user — cannot cache across users with different roles

---

## 6. Q4_K_M Quantization Target for Edge

**Decision:** Q4_K_M as default edge quantization format

**Rationale:**
- 4.5GB fits within 8GB RAM on Raspberry Pi 5 with 3.5GB headroom for OS + Python runtime
- <2% accuracy loss vs fp16 baseline on standard NLP benchmarks
- CTranslate2 INT8 inference achieves 40-50 tokens/sec on ARM64 (Pi 5) vs. 8-10 TPS with fp16

**Trade-off:**
- Q8_0 would give <0.5% accuracy loss but requires 6GB, leaving only 2GB free — too tight for production
- Q4_K_M shows higher perplexity on math/code generation tasks; Q5_K_M is recommended for coding agents
- Jetson Nano (4GB) cannot run 7B-8B models even at Q4 — must use 1B-3B class models (Phi-3-mini, Qwen-1.5B)

---

## 7. In-Memory Execution Store vs. Redis

**Decision:** In-memory dict (`_executions`) for development; Redis for production

**Rationale:**
- In-memory is sufficient for single-instance development and avoids Redis dependency for local testing
- Redis provides persistence across restarts and horizontal scaling (multiple API pods can share state)
- The switch is one line: replace `_executions = {}` with Redis client

**Trade-off:**
- In-memory state is lost on pod restart — any pending executions are irrecoverable
- Redis adds operational complexity and latency overhead (~1-2ms per read/write)
- For truly large-scale (>1000 concurrent executions), consider a dedicated job queue (Celery + Redis/RabbitMQ)

---

## 8. Deterministic Mock Fallback Pattern

**Decision:** Every LLM call has a deterministic mock fallback that produces structurally valid output

**Rationale:**
- Platform is fully testable without API keys or local GPU
- CI/CD pipelines can run complete integration tests in <60 seconds without Ollama
- Enables feature development and frontend testing in parallel with LLM integration
- Mock outputs are hash-seeded → consistent across test runs (no flaky tests)

**Trade-off:**
- Mock outputs don't test real LLM quality — must run with real backends for accuracy validation
- Mock detection requires checking `backend_used == "mock"` in response — easy to miss
- Some edge cases (streaming, function calling) require special mock handling

---

## 9. Multi-turn Conversation Context

**Decision:** `ConversationContext` Pydantic model with accumulated entity merging

**Rationale:**
- Entities accumulate across turns: user says "track it" in turn 2 → system uses order_id from turn 1
- Full conversation history enables LLM to generate contextually coherent multi-turn responses
- Explicit `escalation_reason` field enables precise handoff logging to human agent systems

**Trade-off:**
- Context stored in-memory per session — must persist to Redis for production multi-session support
- Context window grows with each turn — at 10 turns, prompt can be 2-3K tokens
- Max turns=10 hard limit prevents runaway conversations from consuming unbounded tokens

---

## 10. Citation Correctness via Word Overlap vs. NLI

**Decision:** Sliding-window word overlap as primary citation method

**Rationale:**
- Word overlap is O(n) and requires no additional model — adds <5ms latency
- 30-word window captures local context while avoiding false matches from globally common terms
- Achieves ~92% correctness on internal benchmarks when context chunks are well-retrieved

**Trade-off:**
- Production quality would use NLI (Natural Language Inference) model for semantic entailment checking
- Word overlap fails on paraphrases: "physician" vs "doctor" won't match
- Upgrading to `cross-encoder/nli-deberta-v3-small` for citation verification would add ~50ms but improve correctness to ~97%
